import asyncio
import json

import goodwe
import time

from config import generalConfig as c, inverterConfig
from common import connect_mqtt, publishProperties


async def publish(client):
    inverter = await goodwe.connect(host=inverterConfig["ip_address"], retries=10, timeout=5)
    while True:
        runtime_data = await inverter.read_runtime_data()

        client.publish("home/FVE/power/1", runtime_data["ppv1"], qos=2, properties=publishProperties)
        client.publish("home/FVE/power/2", runtime_data["ppv2"], qos=2, properties=publishProperties)
        client.publish("home/FVE/power/all", runtime_data["ppv"], qos=2, properties=publishProperties)
        client.publish("home/FVE/consumption", runtime_data["house_consumption"], qos=2, properties=publishProperties)
        client.publish("home/FVE/battery_load", runtime_data["pbattery1"], qos=2, properties=publishProperties)
        client.publish("home/FVE/curr/1", runtime_data["igrid"], qos=2, properties=publishProperties)
        client.publish("home/FVE/curr/2", runtime_data["igrid2"], qos=2, properties=publishProperties)
        client.publish("home/FVE/curr/3", runtime_data["igrid3"], qos=2, properties=publishProperties)
        client.publish("home/FVE/apparent_power", runtime_data["apparent_power"], qos=2, properties=publishProperties)
        client.publish("home/FVE/reactive_power", runtime_data["reactive_power"], qos=2, properties=publishProperties)
        client.publish("home/FVE/active_power", runtime_data["active_power"], qos=2, properties=publishProperties)
        client.publish("home/FVE/meter_power", runtime_data["meter_active_power_total"], qos=2, properties=publishProperties)
        client.publish("home/FVE/total_inverter_power", runtime_data["total_inverter_power"], qos=2, properties=publishProperties)
        client.publish("home/FVE/inverter_temp_air", runtime_data["temperature_air"], qos=2, properties=publishProperties)
        client.publish("home/FVE/inverter_temp_rad", runtime_data["temperature"], qos=2, properties=publishProperties)
        client.publish("home/FVE/battery/total/battery_charged", runtime_data["e_bat_charge_total"], qos=2, properties=publishProperties)
        client.publish("home/FVE/battery/total/battery_discharged", runtime_data["e_bat_discharge_total"], qos=2, properties=publishProperties)
        client.publish("home/FVE/battery/day/battery_charged", runtime_data["e_bat_charge_day"], qos=2, properties=publishProperties)
        client.publish("home/FVE/battery/day/battery_discharged", runtime_data["e_bat_discharge_day"], qos=2, properties=publishProperties)
        client.publish("home/FVE/generation_day", runtime_data["e_day"], qos=2, properties=publishProperties)
        client.publish("home/FVE/consumption_day", runtime_data["e_load_day"], qos=2, properties=publishProperties)
        client.publish("home/FVE/soc", runtime_data["battery_soc"], qos=2, properties=publishProperties)
        client.publish("home/FVE/soh", runtime_data["battery_soh"], qos=2, properties=publishProperties)

        wallbox_only_data = {key: runtime_data[key] for key in ["ppv", "load_p1", "load_p2", "load_p3", "backup_i1", "backup_i2", "backup_i3", "battery_soc"]}
        client.publish("wallbox/inverter", json.dumps(wallbox_only_data))  # Wallbox only needs the latest data when it is online, so qos = 0

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
            client.publish("diag/FVE", diag, qos=2, properties=publishProperties)

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
