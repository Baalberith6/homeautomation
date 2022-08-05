import asyncio
import math
import time
from os import truncate

import goodwe
from config import influxConfig, inverterConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# keep at least 1A diff
def calculate(arr, actual_charging_current):
    # kanvica do bat - 1900 pgrid2, 1900 backup_p2
    # bat na 1.9 - pgrid 3x 1000 + 3000 active p
    # traktor a bat - load_p1 1450, 1650 active, 1900 bat, 5700 tot, total_inverter_power = 3491 W
    # max 9000 / 3 per phase

    stop_at = 6  # Amp
    start_at = 6
    max_amp = 14.5
    should_charge = True
    was_charging = actual_charging_current != 0

    max_i1 = max_amp - (arr["load_p1"] / 230 + arr["backup_i1"])
    max_i2 = max_amp - (arr["load_p2"] / 230 + arr["backup_i2"])
    max_i3 = max_amp - (arr["load_p3"] / 230 + arr["backup_i3"])
    max_possible_current = min(max_i1, max_i2, max_i3)
    available_current = min(max_possible_current, (arr["active_power"] / 690) - actual_charging_current)  # 230 * 3
    allowable_current = actual_charging_current + available_current - 0.5  # 345W min. reserve
    allowable_current_capped = min(max_amp - 1, max(stop_at, math.floor(allowable_current)))  # step down by 1A
    would_add = (allowable_current - actual_charging_current)

    if was_charging:
        should_charge = allowable_current >= stop_at or arr["battery_soc"] >= 90
        # print(f"if charging, would charge: {should_charge}, {allowable_current_capped} A")

    if not was_charging:
        should_charge = allowable_current >= start_at
        # print(f"if NOT charging, would charge: {should_charge}, {allowable_current_capped} A")

    if not should_charge:
        return 0
    else:
        return allowable_current_capped

    # print(f"P1 avail {max_i1} A")
    # print(f"P2 avail {max_i2} A")
    # print(f"P3 avail {max_i3} A")
    # print(f"max {max_possible_current} A")
    # print(f"avail {available_current} A")
    # print(f"allowable {allowable_current} A")
    # print(f"would add {would_add} A")


async def store_runtime_data():
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
    previous_charging_curr = 0 if len(previous_charging_curr_arr) == 0 else previous_charging_curr_arr[0].records[0].values["_value"]

    charging_curr = calculate(runtime_data, previous_charging_curr)
    # print(f"prev {previous_charging_curr} A")
    # print(f"now {charging_curr} A")
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("car_charge_amp", int(charging_curr)))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("car_charge_amp", int(0)))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("string", "2").field("power", runtime_data["ppv2"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("string", "all").field("power", runtime_data["ppv"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("direction", runtime_data["grid_in_out_label"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "now").field("consumption", runtime_data["house_consumption"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("battery_load", runtime_data["pbattery1"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("phase", "1").field("curr", runtime_data["igrid"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("phase", "2").field("curr", runtime_data["igrid2"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("phase", "3").field("curr", runtime_data["igrid3"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("apparent_power", runtime_data["apparent_power"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("reactive_power", runtime_data["reactive_power"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("active_power", runtime_data["active_power"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("total_inverter_power", runtime_data["total_inverter_power"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("inverter_temp_air", runtime_data["temperature_air"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("inverter_temp_rad", runtime_data["temperature"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("battery_charged", runtime_data["e_bat_charge_total"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("battery_charged", runtime_data["e_bat_charge_day"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("battery_discharged", runtime_data["e_bat_discharge_total"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("battery_discharged", runtime_data["e_bat_discharge_day"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("generation", runtime_data["e_day"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("consumption_day", runtime_data["e_load_day"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("soc", runtime_data["battery_soc"]))
    # write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("soh", runtime_data["battery_soh"]))
    #
    # diag = runtime_data['diagnose_result_label']\
    #     .replace("Discharge Driver On", "")\
    #     .replace("Self-use load light", "")\
    #     .replace("Battery Overcharged", "")\
    #     .replace("BMS: Charge disabled", "")\
    #     .replace("PF value set", "")\
    #     .replace("Battery SOC low", "")\
    #     .replace("Battery SOC in back", "")\
    #     .replace("SOC delta too volatile", "")
    #
    # while diag.startswith(" ") or diag.startswith(",") or diag.endswith(" ") or diag.endswith(","):
    #     diag = diag.strip(", ")
    #
    # if (len(diag) != 0):
    #     write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("diag", diag))
    # p1 = runtime_data["pgrid"] - runtime_data["backup_p1"]
    # p2 = runtime_data["pgrid2"] - runtime_data["backup_p2"]
    # p3 = runtime_data["pgrid3"] - runtime_data["backup_p3"]

test_data = {
    "igrid": 6.5,
    "igrid2": 6.1,
    "igrid3": 6.1,
    "backup_i1": 0.1,
    "backup_i2": 0.1,
    "backup_i3": 0.1,
    "active_power": 0 * 690 + 0,  # 6.5 * 690 = 4485W min to start, stops at 4485W <97%SoC
    "battery_soc": 98
}
# calculate(test_data, 6)
asyncio.run(store_runtime_data())
# time.sleep(15)

