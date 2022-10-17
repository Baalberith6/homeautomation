import asyncio
import json

import goodwe
import time

from config import generalConfig as c, inverterConfig
from common import connect_mqtt


async def publish(client):
    inverter = await goodwe.connect(inverterConfig["ip_address"])
    while True:
        runtime_data = await inverter.read_runtime_data()

        client.publish("home/FVE/power/1", runtime_data["ppv1"])
        client.publish("home/FVE/power/2", runtime_data["ppv2"])
        client.publish("home/FVE/power/all", runtime_data["ppv"])
        client.publish("home/FVE/consumption", runtime_data["house_consumption"])
        client.publish("home/FVE/battery_load", runtime_data["pbattery1"])
        client.publish("home/FVE/curr/1", runtime_data["igrid"])
        client.publish("home/FVE/curr/2", runtime_data["igrid2"])
        client.publish("home/FVE/curr/3", runtime_data["igrid3"])
        client.publish("home/FVE/apparent_power", runtime_data["apparent_power"])
        client.publish("home/FVE/reactive_power", runtime_data["reactive_power"])
        client.publish("home/FVE/active_power", runtime_data["active_power"])
        client.publish("home/FVE/total_inverter_power", runtime_data["total_inverter_power"])
        client.publish("home/FVE/inverter_temp_air", runtime_data["temperature_air"])
        client.publish("home/FVE/inverter_temp_rad", runtime_data["temperature"])
        client.publish("home/FVE/battery/total/battery_charged", runtime_data["e_bat_charge_total"])
        client.publish("home/FVE/battery/total/battery_discharged", runtime_data["e_bat_discharge_total"])
        client.publish("home/FVE/battery/day/battery_charged", runtime_data["e_bat_charge_day"])
        client.publish("home/FVE/battery/day/battery_discharged", runtime_data["e_bat_discharge_day"])
        client.publish("home/FVE/generation_day", runtime_data["e_day"])
        client.publish("home/FVE/consumption_day", runtime_data["e_load_day"])
        client.publish("home/FVE/soc", runtime_data["battery_soc"])
        client.publish("home/FVE/soh", runtime_data["battery_soh"])

        wallbox_only_data = {key: runtime_data[key] for key in ["ppv", "load_p1", "load_p2", "load_p3", "backup_i1", "backup_i2", "backup_i3", "battery_soc"]}
        client.publish("wallbox/inverter", json.dumps(wallbox_only_data))

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
            client.publish("home/FVE/diag", diag)

        if (c["debug"]):
            print("\n\n\n---INVERTER START---")
            for sensor in inverter.sensors():
                if sensor.id_ in runtime_data:
                    print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")
            print("---INVERTER END---\n\n\n")

        time.sleep(inverterConfig["wait"])


def run():
    client = connect_mqtt("inverter")
    client.loop_start()
    asyncio.run(publish(client))


if __name__ == '__main__':
    run()
