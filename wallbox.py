import math
import json
import time
from json import JSONDecodeError

import requests
from paho.mqtt import client as mqtt_client

from config import generalConfig as c, wallboxConfig

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
from common import connect_mqtt

amp = -1
alw = -1
frc = -1
car = -1
nrg = [0, 0, 0, 0, 0, 0]
modelStatus = -1
updatedAt = -1


def calculate_current(inverter, actual_charging_current: int, car_phases: int):
    # kanvica do bat - 1900 pgrid2, 1900 backup_p2
    # bat na 1.9 - pgrid 3x 1000 + 3000 active p
    # traktor a bat - load_p1 1450, 1650 active, 1900 bat, 5700 tot, total_inverter_power = 3491 W
    # max 9000 / 3 per phase

    stop_at = 6  # Amp
    start_at = 6
    max_amp = 16
    should_charge = True
    was_charging = actual_charging_current != 0

    # current consumption without car charging
    i1 = inverter["load_p1"] / 230 + inverter["backup_i1"]
    i2 = inverter["load_p2"] / 230 + inverter["backup_i2"]
    i3 = inverter["load_p3"] / 230 + inverter["backup_i3"]
    allowable_current = actual_charging_current
    remaining_ppv = inverter["ppv"] - i1 * 230 - i2 * 230 - i3 * 230

    # increase, until we use all PV
    while 0 <= allowable_current - actual_charging_current + math.ceil(max(i1, i2, i3)) < max_amp and remaining_ppv > car_phases * 230 and allowable_current < max_amp:
        remaining_ppv -= car_phases * 230
        allowable_current += 1
        if c["debug"]: print(f"added, ppv: {remaining_ppv}, allowable: {allowable_current}")

    # decrease, if negative PV
    while allowable_current > 0 and remaining_ppv < 0:
        remaining_ppv += car_phases * 230
        allowable_current -= 1
        if c["debug"]: print(f"substracted, ppv: {remaining_ppv}, allowable: {allowable_current}")

    if was_charging:
        should_charge = allowable_current >= stop_at and car_phases == 3 or \
                        (inverter["battery_soc"] >= wallboxConfig["stop_at_soc"] and car_phases == 3) or \
                        (wallboxConfig["stop_at_soc"] <= inverter["battery_soc"] < 100 and car_phases == 1) or \
                        inverter["battery_soc"] < wallboxConfig["stop_at_soc"] - 5
        if inverter["battery_soc"] < wallboxConfig["stop_at_soc"] - 5:  # manual start, so keep the manual amps if 5 below limit soc
            allowable_current = actual_charging_current
        elif allowable_current < stop_at:
            allowable_current = stop_at  # we want to continue with the slowest speed possible
        if c["debug"]: print(f"if charging, would charge: {should_charge}, {allowable_current} A")

    if not was_charging:
        should_charge = allowable_current >= start_at and wallboxConfig["start_at_soc"] < inverter["battery_soc"] < 100
        if c["debug"]: print(f"if NOT charging, would charge: {should_charge}, {allowable_current} A")

    if c["debug"]: print(f"P1 curr {i1} A")
    if c["debug"]: print(f"P2 curr {i2} A")
    if c["debug"]: print(f"P3 curr {i3} A")
    if c["debug"]: print(f"actual charging current {actual_charging_current} A")
    if c["debug"]: print(f"PPV {inverter['ppv']} W")
    if c["debug"]: print(f"allowable {allowable_current} A")

    if not should_charge:
        return 0
    else:
        return allowable_current


def wallbox(inverter, client):
    if updatedAt < (time.time() - 10):  # 10 sec timeout
        if c["debug"]: print("Wallbox is OFFLINE")
        return

    phases = 0
    if nrg[4] > 1: phases += 1
    if nrg[5] > 1: phases += 1
    if nrg[6] > 1: phases += 1
    if phases != 1: phases = 3  # we don't know the number of connected phases before starting, also safe-default to 3 except when 1
    if c["debug"]: print(f"phases: {phases}")

    if car in [0, 1, 5]:  # no 4 as Golf kept starting, but Enyaq wont start then
        if c["debug"]: print(f"no charge allowed - perhaps car not connected or doesn't want to charge, car state {car}")
        if frc != 1:
            if c["debug"]: print("setting force state to disabled")
            client.publish("go-eCharger/201630/frc/set", 1)
            # req.get(wallboxConfig["address"] + 'api/set?frc=1')
        return  # no charge allowed - perhaps car not connected, doesn't want to charge or disabled in app?
    if modelStatus == 22:
        if c["debug"]: print("NotChargingBecauseSimulateUnplugging")
        return  # NotChargingBecauseSimulateUnplugging
    previous_charging_curr = amp if frc == 0 and car != 4 else 0  # if charging allowed and already charging

    charging_curr = calculate_current(inverter, previous_charging_curr, phases)

    if frc == 1 and charging_curr > 0:  # stopped, but should start
        if c["debug"]: print(f"stopped, but should start, {charging_curr}A")
        client.publish("go-eCharger/201630/amp/set", charging_curr)
        client.publish("go-eCharger/201630/frc/set", 0)
        # req.get(wallboxConfig["address"] + 'api/set?amp={charging_curr}&frc=0')
    if frc == 0 and charging_curr > 0:  # started, just change amp
        if amp == charging_curr:
            if c["debug"]: print(f"started, do nothing, {charging_curr}A")
            return
        #       do nothing
        else:
            if c["debug"]: print(f"started, just change amp, {charging_curr}A")
            client.publish("go-eCharger/201630/amp/set", charging_curr)
            # req.get(f'{wallboxConfig["address"]}api/set?amp={charging_curr}')
    if frc == 1 and charging_curr == 0:  # stopped, shouldn't start
        if c["debug"]: print(f"stopped, shouldn't start, {charging_curr}A")
        return
        # do nothing
    if frc == 0 and charging_curr == 0:  # started, should stop
        if c["debug"]: print(f"started, should stop, {charging_curr}A")
        client.publish("go-eCharger/201630/frc/set", 1)
        # req.get(wallboxConfig["address"] + 'api/set?frc=1')


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        # if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        topicParts = msg.topic.split("/")
        if topicParts[0] == "go-eCharger" and topicParts[-1] in ["amp", "alw", "frc", "car", "nrg", "modelStatus"]:
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global amp, alw, frc, car, nrg, modelStatus, updatedAt
            if topicParts[-1] == "amp": amp = int(msg.payload.decode())
            if topicParts[-1] == "alw": alw = bool(msg.payload.decode())
            if topicParts[-1] == "frc": frc = int(msg.payload.decode())
            if topicParts[-1] == "car": car = int(msg.payload.decode())
            if topicParts[-1] == "nrg":
                nrg = list(map(float, msg.payload.decode().strip('][').split(',')))
                client.publish("home/Car/charging_wallbox_power", nrg[11])
            if topicParts[-1] == "modelStatus": modelStatus = int(msg.payload.decode())
            updatedAt = time.time()
        elif topicParts[0] == "wallbox":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            wallbox(json.loads(msg.payload), client)

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    try:
        response = requests.get(wallboxConfig["address"] + 'api/status?filter=amp,alw,frc,car,nrg,modelStatus')
        res = json.loads(response.text)
        global amp, alw, frc, car, nrg, modelStatus, updatedAt
        amp = res["amp"]
        alw = res["alw"]
        frc = res["frc"]
        car = res["car"]
        nrg = res["nrg"]
        modelStatus = res["modelStatus"]
        updatedAt = time.time()
    except JSONDecodeError:
        print("error connecting to Wallbox")
        return
    client = connect_mqtt("wallbox")
    subscribe(client, ["wallbox/inverter", "go-eCharger/201630/#"])
    client.loop_forever()


if __name__ == '__main__':
    run()
