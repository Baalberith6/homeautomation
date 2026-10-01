import asyncio
import json
import sys
import threading
import time
from datetime import datetime, timedelta

from estia_api import (LoginBackoff, ToshibaAcHttpApi, ToshibaAcHttpApiAuthError, ToshibaAcHttpApiError,
                       ToshibaAcHttpApiRateLimitError)

sys.stdout.reconfigure(line_buffering=True)

from paho.mqtt import client as mqtt_client  # noqa: E402
from common import HTTP_ALERT_AFTER, ConnectionLog, connect_mqtt, get_logger, setup_logging, subscribe_on_connect  # noqa: E402
from config import influxConfig  # noqa: E402
from secret import toshibaUsername, toshibaSecret, influxToken  # noqa: E402
from config import generalConfig as c, estiaConfig  # noqa: E402
from influxdb_client import InfluxDBClient, Point  # noqa: E402
from influxdb_client.client.write_api import SYNCHRONOUS  # noqa: E402

# once per hour at minute 22, calc COP for the last 24h

log = get_logger("estia_energy")
# After a 403 or 429 on the consumption call: keep the token and try again in 5 min, then 10, 30,
# 60 min; a COP resets it (change 019 revision 4). A retry 5-6 min after a 403 worked 4 of 4 times.
DATA_RETRY_STEPS = (300, 600, 1800, 3600)
# WARNING while the consumption call fails for less than an hour, then ERROR (fires R3).
cop_log = ConnectionLog(log, "Toshiba consumption", grace=3600, alert_after=HTTP_ALERT_AFTER)

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# This service's own Device-ID for the Toshiba firewall (change 019, revision 2).
DEVICE_ID = "14c2a40d2951f0e0"
TOKEN_PATH = "toshiba_token_estia_energy.dev.json" if c["debug"] else "toshiba_token_estia_energy.json"
api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret, device_id=DEVICE_ID, token_path=TOKEN_PATH)
heat_loss = 143 # W/K
temps = [18] * 24


def merge_arrays(arr1, arr2):
    merged_array = []
    last_val2 = 0
    switch_to_second = False

    for val1, val2 in zip(arr1, arr2):
        if switch_to_second:
            merged_array.append(val2)
        else:
            if val1 == 0:
                if len(merged_array) > 0:
                    merged_array.pop()
                    merged_array.append(last_val2)
                merged_array.append(val2)
                switch_to_second = True
            else:
                merged_array.append(val1)
        last_val2 = val2

    return merged_array


def replace_two_highest_with(numbers, replacement):
    highest = second_highest = float('-inf')
    highest_index = second_highest_index = -1

    for i, number in enumerate(numbers):
        if number > highest:
            second_highest, second_highest_index = highest, highest_index
            highest, highest_index = number, i
        elif number > second_highest:
            second_highest, second_highest_index = number, i

    # Replace the two highest values with 200, maintaining the original order
    if highest_index != -1:
        numbers[highest_index] = replacement
    # As of now, we only heat TUV once a day
    # if second_highest_index != -1:
    #    numbers[second_highest_index] = replacement

    return numbers

def calculate_cop(consumption_24h: list, temp_avgs_24h: list):
    if c["debug"]: print(f"today consumption: {consumption_24h},\ntemps: {temp_avgs_24h}")

    cop = 0
    total_consumption = 0

    # fix for TUV:
    replace_two_highest_with(consumption_24h, 200)

    for hourly_temp, hourly_consumption in zip(temp_avgs_24h, consumption_24h):
        if hourly_temp > 17:
            continue
        if hourly_consumption == 0:
            hourly_consumption = 1 # if no data or TUV too much, assume 1W

        new_cop = (heat_loss * (18 - hourly_temp)) / hourly_consumption
        cop = (total_consumption * cop + hourly_consumption * new_cop) / (hourly_consumption + total_consumption)
        if c["debug"]: print(f"HOURLY: {hourly_temp}C   {hourly_consumption}Wh  -> COP {cop}")
        total_consumption += hourly_consumption

    if c["debug"]: print(f"COP: {cop}")
    return cop, total_consumption

def new_state():
    """Loop state: token, a due hourly COP, and the earliest next Toshiba try."""
    return {"logged_in": False, "due": False, "due_hour": None, "next_try": 0.0, "data_failures": 0}


async def fetch_consumption(api):
    """The rolling 24 h of hourly consumption, in Wh, from the Toshiba cloud.

    A Toshiba error names the call that failed, "(today)" or "(yesterday)" (change 019 revision 4).
    """
    device = estiaConfig["device_unique_id"]
    try:
        today = (await api.get_hourly_consumption(device, datetime.now()))[0]["EnergyConsumption"]
    except ToshibaAcHttpApiError as e:
        raise type(e)(f"{e} (today)") from e
    try:
        yesterday = (await api.get_hourly_consumption(device, datetime.now() - timedelta(days=1)))[0]["EnergyConsumption"]
    except ToshibaAcHttpApiError as e:
        raise type(e)(f"{e} (yesterday)") from e
    if c["debug"]:
        print(f"Received Today Hourly usages: `{today}` from Toshiba")
        print(f"Received Yesterday Hourly usages: `{yesterday}` from Toshiba")
    return merge_arrays([item["Energy"] for item in today], [item["Energy"] for item in yesterday])


async def tick(api, state, backoff, now, mono):
    """One minute of the COP loop (change 019).

    The COP falls due at minute 22, once per hour. A failed login waits for the
    login backoff. A 403 or 429 on the consumption call keeps the token and
    waits for DATA_RETRY_STEPS (revision 4). The due COP stays due until a try
    works. `now` is the wall clock, `mono` a monotonic time in seconds.
    """
    hour = now.strftime("%Y%m%d%H")
    if now.minute == 22 and state["due_hour"] != hour:
        state["due"] = True
        state["due_hour"] = hour
    if state["logged_in"] and not state["due"]:
        return
    if mono < state["next_try"]:
        return

    try:
        if not state["logged_in"]:
            source = await api.connect()
            await api.get_devices()
            state["logged_in"] = True
            log.info(f"Toshiba login OK ({source})")
        usage = await fetch_consumption(api) if state["due"] else None
        backoff.success(mono)
    except ToshibaAcHttpApiRateLimitError as e:
        if state["logged_in"]:
            # The login worked or was not needed, so the consumption call failed: keep the token.
            delay = DATA_RETRY_STEPS[min(state["data_failures"], len(DATA_RETRY_STEPS) - 1)]
            state["data_failures"] += 1
            state["next_try"] = mono + delay
            cop_log.failed(f"{e}; next try in {delay} s")
            return
        state["logged_in"] = False
        delay = backoff.failure(mono)
        if delay >= backoff.last_step:
            api.forget_token()
        state["next_try"] = mono + delay
        log.error(f"Toshiba error: {e}; next login in {delay} s")
        return
    except Exception as e:
        state["logged_in"] = False
        delay = backoff.failure(mono)
        if isinstance(e, ToshibaAcHttpApiAuthError) or delay >= backoff.last_step:
            api.forget_token()
        state["next_try"] = mono + delay
        log.error(f"Toshiba error: {e}; next login in {delay} s")
        return

    if usage is None:
        return
    state["data_failures"] = 0
    cop_log.ok()
    state["due"] = False
    if c["debug"]:
        print(f"Merged Hourly usages: `{usage}` from Toshiba")
    try:
        cop, total_consumption = calculate_cop(usage, temps)
    except Exception as e:
        log.error(f"COP error: {e}")
        return
    try:
        write_api.write(bucket=influxConfig["bucket"], record=Point("Estia").field("cop_24h", float(cop)))
        write_api.write(bucket=influxConfig["bucket"],
                        record=Point("Estia").field("consumption_24h", float(total_consumption)))
    except Exception as e:
        log.error(f"InfluxDB error: {e}")


async def calc():
    await asyncio.sleep(60)  # wait for temps to arrive
    state = new_state()
    backoff = LoginBackoff()
    while True:
        await tick(api, state, backoff, datetime.now(), time.monotonic())
        await asyncio.sleep(60)


def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(calc())
    loop.close()

def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        global temps
        temps = json.loads(msg.payload)
        if c["debug"]: print(f"Received `{temps}` from `{msg.topic}` topic")

    subscribe_on_connect(client, topics)
    client.on_message = on_message

def run():
    client = connect_mqtt("estia_energy")
    subscribe(client, ["jsons/weather/local/temps_24h"])
    threading.Thread(target=start_async_loop, daemon=True).start()
    client.loop_forever()

if __name__ == '__main__':
    setup_logging()
    run()
