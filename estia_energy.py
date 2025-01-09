import asyncio
import json
import threading
from datetime import datetime, timedelta

from estia_api import ToshibaAcHttpApi

from paho.mqtt import client as mqtt_client
from common import connect_mqtt
from config import influxConfig
from secret import toshibaUsername, toshibaSecret, influxToken
from config import generalConfig as c, estiaConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# every 5 min, calc COP for last 24h

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret)
connected = False
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

async def calc():
    global connected, api

    await asyncio.sleep(60) # wait for temps to arrive
    await api.connect()
    await api.get_devices()

    while True:
        if datetime.now().minute != 22: # wait for 15 past
            await asyncio.sleep(60)
            continue
        hourly_usage = (await api.get_hourly_consumption(estiaConfig["device_unique_id"], datetime.now()))[0]["EnergyConsumption"]
        hourly_usage_yesterday = (await api.get_hourly_consumption(estiaConfig["device_unique_id"], datetime.now() - timedelta(days=1)))[0]["EnergyConsumption"]
        hourly_usage_merged = merge_arrays([item["Energy"] for item in hourly_usage], [item["Energy"] for item in hourly_usage_yesterday])

        if c["debug"]: print(f"Received Today Hourly usages: `{hourly_usage}` from Toshiba")
        if c["debug"]: print(f"Received Yesterday Hourly usages: `{hourly_usage_yesterday}` from Toshiba")
        if c["debug"]: print(f"Merged Hourly usages: `{hourly_usage_merged}` from Toshiba")

        cop, total_consumption = calculate_cop(hourly_usage_merged, temps)
        write_api.write(bucket=influxConfig["bucket"], record=Point("Estia").field("cop_24h", float(cop)))
        write_api.write(bucket=influxConfig["bucket"], record=Point("Estia").field("consumption_24h", float(total_consumption)))
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

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt("estia_energy")
    subscribe(client, ["jsons/weather/local/temps_24h"])
    threading.Thread(target=start_async_loop, daemon=True).start()
    client.loop_forever()

if __name__ == '__main__':
    run()
