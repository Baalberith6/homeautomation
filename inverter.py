import asyncio

import goodwe
from config import generalConfig as c, influxConfig, inverterConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from wallbox import wallbox


async def inverter():
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    inverter = await goodwe.connect(inverterConfig["ip_address"])
    runtime_data = await inverter.read_runtime_data()

    wallbox_task = asyncio.create_task(wallbox(runtime_data))
    db_task = asyncio.create_task(store_db(runtime_data, write_api))

    if (c["debug"]):
        print("\n\n\n---INVERTER START---")
        for sensor in inverter.sensors():
            if sensor.id_ in runtime_data:
                print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")
        print("---INVERTER END---\n\n\n")

    await wallbox_task
    await db_task


async def store_db(runtime_data, write_api):
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("string", "1").field("power", runtime_data["ppv1"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("string", "2").field("power", runtime_data["ppv2"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("string", "all").field("power", runtime_data["ppv"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("direction", runtime_data["grid_in_out_label"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("sum", "now").field("consumption", runtime_data["house_consumption"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("battery_load", runtime_data["pbattery1"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("phase", "1").field("curr", runtime_data["igrid"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("phase", "2").field("curr", runtime_data["igrid2"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("phase", "3").field("curr", runtime_data["igrid3"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("apparent_power", runtime_data["apparent_power"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("reactive_power", runtime_data["reactive_power"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("active_power", runtime_data["active_power"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("total_inverter_power", runtime_data["total_inverter_power"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("inverter_temp_air", runtime_data["temperature_air"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").field("inverter_temp_rad", runtime_data["temperature"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").tag("sum", "total").field("battery_charged",
                                                                                                 runtime_data[
                                                                                                     "e_bat_charge_total"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("sum", "today").field("battery_charged", runtime_data["e_bat_charge_day"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").tag("sum", "total").field("battery_discharged",
                                                                                                 runtime_data[
                                                                                                     "e_bat_discharge_total"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").tag("sum", "today").field("battery_discharged",
                                                                                                 runtime_data[
                                                                                                     "e_bat_discharge_day"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("sum", "today").field("generation", runtime_data["e_day"]))
    write_api.write(bucket=influxConfig["bucket"],
                    record=Point("FVE").tag("sum", "today").field("consumption_day", runtime_data["e_load_day"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("soc", runtime_data["battery_soc"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("soh", runtime_data["battery_soh"]))
    diag = runtime_data['diagnose_result_label'] \
        .replace("Discharge Driver On", "") \
        .replace("Self-use load light", "") \
        .replace("Battery Overcharged", "") \
        .replace("BMS: Charge disabled", "") \
        .replace("PF value set", "") \
        .replace("Battery SOC low", "") \
        .replace("Battery SOC in back", "") \
        .replace("SOC delta too volatile", "")
    while diag.startswith(" ") or diag.startswith(",") or diag.endswith(" ") or diag.endswith(","):
        diag = diag.strip(", ")
    if (len(diag) != 0):
        write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("diag", diag))


asyncio.run(inverter())
