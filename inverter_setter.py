import asyncio

import goodwe

from config import generalConfig as c, inverterConfig
from common import connect_mqtt
from paho.mqtt import client as mqtt_client

soc = 0
stop_charging_at_soc = 90
last_curr_set = -1
last_dod_set = -1

def charging_curve(x):
    if x <= 40:
        return 15
    elif x <= 60:
        return 10
    elif x == 70:
        return 8
    elif x == 80:
        return 6
    elif x == 90:
        return 4
    elif x >= 95:
        return 2
    else:
        return 10  # or some default if needed


async def handle_inverter_battery_charge_current():
    global last_curr_set
    val = 0 if soc >= stop_charging_at_soc else charging_curve(soc)
    if val != last_curr_set:
        inverter = await goodwe.connect(inverterConfig["ip_address"])
        last_curr_set = val
        if c["debug"]: print(f"Setting `{val}` for battery_charge_current")
        await inverter.write_setting("battery_charge_current", val)
    else:
        if c["debug"]: print(f"No change... `{val}` for battery_charge_current")


async def handle_inverter_depth_of_discharge(val):
    global last_dod_set
    if val != last_dod_set:
        last_dod_set = val
        inverter = await goodwe.connect(inverterConfig["ip_address"])
        if c["debug"]: print(f"Setting `{val}` for dod")
        await inverter.set_ongrid_battery_dod(val)
    else:
        if c["debug"]: print(f"No change... `{val}` for dod")


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        # if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        topicParts = msg.topic.split("/")
        if topicParts[1] == "InverterDepthOfDischarge":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            asyncio.run(handle_inverter_depth_of_discharge(int(msg.payload.decode())))
        elif topicParts[1] == "InverterStopChargingAt":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global stop_charging_at_soc
            stop_charging_at_soc = int(msg.payload.decode())
            asyncio.run(handle_inverter_battery_charge_current())
        elif topicParts[1] == "FVE":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global soc
            soc = int(msg.payload.decode())
            asyncio.run(handle_inverter_battery_charge_current())

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt("inverter_setter")
    subscribe(client, ["command/InverterDepthOfDischarge", "command/InverterStopChargingAt", "home/FVE/soc"])
    client.loop_forever()


if __name__ == '__main__':
    run()
