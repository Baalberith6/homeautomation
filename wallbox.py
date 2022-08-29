import asyncio
import math
import json
import time
from os import truncate
import requests as req

import goodwe
from config import influxConfig, inverterConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


# adjust amps
# curl "http://1.2.3.4/api/set?amp=16"

# set 1-phase
# curl "http://1.2.3.4/api/set?psm=1"

# set 3-phase
# curl "http://1.2.3.4/api/set?psm=2"

# start charging
# curl "http://1.2.3.4/api/set?frc=0"

# stop charging
# curl "http://1.2.3.4/api/set?frc=1"

# Get settings (all or some, see https://github.com/goecharger/go-eCharg ... keys-de.md ):
# curl "http://1.2.3.4/api/status"
# curl "http://1.2.3.4/api/status?filter=amp,psm"

# keep at least 1A diff
def calculate_current(inverter, actual_charging_current):
    # kanvica do bat - 1900 pgrid2, 1900 backup_p2
    # bat na 1.9 - pgrid 3x 1000 + 3000 active p
    # traktor a bat - load_p1 1450, 1650 active, 1900 bat, 5700 tot, total_inverter_power = 3491 W
    # max 9000 / 3 per phase

    stop_at = 6  # Amp
    start_at = 6
    max_amp = 14.5
    should_charge = True
    was_charging = actual_charging_current != 0

    max_i1 = max_amp - (inverter["load_p1"] / 230 + inverter["backup_i1"])
    max_i2 = max_amp - (inverter["load_p2"] / 230 + inverter["backup_i2"])
    max_i3 = max_amp - (inverter["load_p3"] / 230 + inverter["backup_i3"])
    max_possible_current = min(max_i1, max_i2, max_i3)
    available_current = min(max_possible_current, (inverter["active_power"] / 690) - actual_charging_current)  # 230 * 3
    allowable_current = actual_charging_current + available_current - 0.2  # 345W min. reserve
    allowable_current_capped = min(max_amp - 1, max(stop_at, math.floor(allowable_current)))  # step down by 1A
    would_add = (allowable_current - actual_charging_current)

    if was_charging:
        should_charge = allowable_current >= stop_at or inverter["battery_soc"] >= 80
        # print(f"if charging, would charge: {should_charge}, {allowable_current_capped} A")

    if not was_charging:
        should_charge = allowable_current >= start_at
        # print(f"if NOT charging, would charge: {should_charge}, {allowable_current_capped} A")

    # print(f"P1 avail {max_i1} A")
    # print(f"P2 avail {max_i2} A")
    # print(f"P3 avail {max_i3} A")
    # print(f"max {max_possible_current} A")
    # print(f"avail {available_current} A")
    # print(f"allowable {allowable_current} A")
    # print(f"would add {would_add} A")

    if not should_charge:
        return 0
    else:
        return allowable_current_capped


async def wallbox():
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)
    read_api = client.query_api()

    inverter = await goodwe.connect(inverterConfig["ip_address"])
    runtime_data = await inverter.read_runtime_data()

    # for sensor in inverter.sensors():
    #     if sensor.id_ in runtime_data:
    #         print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")

    bucket = influxConfig["bucket"]

    previous_charging_curr_arr = read_api.query(f'''
             from(bucket:"{bucket}") |> range(start: -5m)
                 |> filter(fn: (r) => r["_measurement"] == "FVE")
                 |> filter(fn: (r) => r["_field"] == "car_charge_amp")
                 |> last()
             ''')
    previous_charging_curr = 0 if len(previous_charging_curr_arr) == 0 else \
        previous_charging_curr_arr[0].records[0].values["_value"]

    # req.get('http://192.168.1.118/api/status?filter=amp,alw,frc')
    # res = json.loads(response.text)
    # if !res["alw"]:
    #    return; # no charge allowed - perhaps car not connected?
    # previous_charging_curr = res["amp"] if res["frc"] == 0 else 0

    charging_curr = calculate_current(runtime_data, previous_charging_curr)

    # req.get('http://192.168.1.118/api/set?amp={charging_curr}')
    # if res["frc"] == 1 && charging_curr > 0: # stopped, but should start
    # req.get('http://192.168.1.118/api/set?amp={charging_curr}&frc=0')
    # if res["frc"] == 0 && charging_curr > 0: # started, just change amp
    #    if (res["amp"] == charging_curr)
    #       do nothing
    #    else
    #       req.get('http://192.168.1.118/api/set?amp={charging_curr}')
    # if res["frc"] == 1 && charging_curr == 0: # stopped, shouldn't start
    # do nothing
    # if res["frc"] == 0 && charging_curr == 0: # started, should stop
    # req.get('http://192.168.1.118/api/set?frc=1')

    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("car_charge_amp", int(charging_curr)))


test_data = {
    "load_p1": 6.5,
    "load_p2": 6.1,
    "load_p3": 6.1,
    "backup_i1": 0.1,
    "backup_i2": 0.1,
    "backup_i3": 0.1,
    "active_power": 0 * 690 + 0,  # 6.5 * 690 = 4485W min to start, stops at 4485W <97%SoC
    "battery_soc": 98
}
# calculate_current(test_data, 6)
asyncio.run(wallbox())
# time.sleep(15)
