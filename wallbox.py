import math
import json
import time
from json import JSONDecodeError

import requests
from paho.mqtt import client as mqtt_client

from config import generalConfig as c, wallboxConfig

# adjust amps
# curl "http://1.2.3.4/api/set?amp=16"

# start charging
# curl "http://1.2.3.4/api/set?frc=0"

# stop charging
# curl "http://1.2.3.4/api/set?frc=1"

# Get settings (all or some, see https://github.com/goecharger/go-eCharg ... keys-de.md ):
# curl "http://1.2.3.4/api/status"
# curl "http://1.2.3.4/api/status?filter=amp,psm"

# keep at least 1A diff
from common import connect_mqtt

wallboxMode = "Auto"
wallboxMaxAmp = 16
wallboxStartSOC = 40
wallboxStopAtSOCDiff = 3
amp = -1
alw = -1
frc = -1
car = -1
nrg = [0, 0, 0, 0, 0, 0]
modelStatus = -1
updatedAt = -1
amp_reserve = -1 # <-1 - faster than PV can provide
maxSocWhileCharging = 0 # if below x constant, then stop charging


def calculate_current(inverter, actual_charging_current: int):
    stop_at = 6  # Amp
    start_at = 6
    phases = 3
    should_charge = True
    was_charging = actual_charging_current != 0

    global maxSocWhileCharging # update max SoC achieved during this charging session
    maxSocWhileCharging = max(inverter["battery_soc"], maxSocWhileCharging)
    if c["debug"]: print(f"maxSocWhileCharging `{maxSocWhileCharging}%`")

    # current consumption without car charging
    i1 = inverter["load_p1"] / 230 + inverter["backup_i1"]
    i2 = inverter["load_p2"] / 230 + inverter["backup_i2"]
    i3 = inverter["load_p3"] / 230 + inverter["backup_i3"]
    allowable_current = actual_charging_current
    remaining_ppv = inverter["ppv"] - i1 * 230 - i2 * 230 - i3 * 230 - amp_reserve * phases * 230

    # increase, until we use all PV
    while 0 <= allowable_current - actual_charging_current + math.ceil(max(i1, i2, i3)) < wallboxMaxAmp and remaining_ppv > phases * 230 and allowable_current < wallboxMaxAmp:
        remaining_ppv -= phases * 230
        allowable_current += 1
        if c["debug"]: print(f"added, ppv: {remaining_ppv}, allowable: {allowable_current}")

    # decrease, if negative PV
    while allowable_current > 0 and remaining_ppv < 0 :
        remaining_ppv += phases * 230
        allowable_current -= 1
        if c["debug"]: print(f"substracted, ppv: {remaining_ppv}, allowable: {allowable_current}")

    if wallboxMode == "Start":
        allowable_current = wallboxMaxAmp
        if c["debug"]: print(f"Overridden current due to Auto mode, allowable: {allowable_current}")

    if wallboxMode == "Auto":
        allowable_current = min(wallboxMaxAmp, allowable_current)
        if c["debug"]: print(f"Overridden current, allowable: {allowable_current}")

    if was_charging:
        should_charge = (allowable_current >= stop_at and wallboxMode == "Auto") or \
                        (inverter["battery_soc"] >= maxSocWhileCharging - wallboxStopAtSOCDiff and wallboxMode == "Auto")  or \
                        wallboxMode == "Start"
#        if inverter["battery_soc"] < wallboxConfig["stop_at_soc"] - 5:  # manual start, so keep the manual amps if 5 below limit soc
#            allowable_current = actual_charging_current
        if allowable_current < stop_at:
            allowable_current = stop_at  # we want to continue with the slowest speed possible
        if c["debug"]: print(f"if charging, would charge: {should_charge}, {allowable_current} A")

    if not was_charging:
        should_charge = (allowable_current >= start_at and wallboxStartSOC < inverter["battery_soc"] and wallboxMode == "Auto") or \
                        wallboxMode == "Start"
        if c["debug"]: print(f"if NOT charging, would charge: {should_charge}, {allowable_current} A")

    if c["debug"]: print(f"P1 curr {i1} A")
    if c["debug"]: print(f"P2 curr {i2} A")
    if c["debug"]: print(f"P3 curr {i3} A")
    if c["debug"]: print(f"actual charging current {actual_charging_current} A")
    if c["debug"]: print(f"PPV {inverter['ppv']} W")
    if c["debug"]: print(f"allowable {allowable_current} A")

    if not should_charge:
        maxSocWhileCharging = 0
        return 0
    else:
        return allowable_current


def wallbox(inverter, client):
    if updatedAt < (time.time() - 10):  # 10 sec timeout
        print("[wallbox] Wallbox is OFFLINE")
        return

    if wallboxMode == "Disable": # automation OFF
        return

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

    charging_curr = calculate_current(inverter, previous_charging_curr)

    if frc == 1 and charging_curr > 0:  # stopped, but should start
        print(f"[wallbox] Started charging at {charging_curr}A")
        client.publish("go-eCharger/201630/amp/set", charging_curr)
        client.publish("go-eCharger/201630/frc/set", 0)
        # req.get(wallboxConfig["address"] + 'api/set?amp={charging_curr}&frc=0')
    if frc == 0 and charging_curr > 0:  # started, just change amp
        if amp == charging_curr:
            if c["debug"]: print(f"[wallbox] No change, {charging_curr}A")
            return
        #       do nothing
        else:
            print(f"[wallbox] Changed amps: {amp}A -> {charging_curr}A")
            client.publish("go-eCharger/201630/amp/set", charging_curr)
            # req.get(f'{wallboxConfig["address"]}api/set?amp={charging_curr}')
    if frc == 1 and charging_curr == 0:  # stopped, shouldn't start
        if c["debug"]: print(f"stopped, shouldn't start, {charging_curr}A")
        return
        # do nothing
    if frc == 0 and charging_curr == 0 and previous_charging_curr > 0:  # started, should stop
        print(f"[wallbox] Stopped charging (was {previous_charging_curr}A)")
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
            if topicParts[-1] == "car":
                    car = int(msg.payload.decode())
                    client.publish("home/Car/car_connected", int(car not in [0, 1, 5]))
            if topicParts[-1] == "nrg":
                nrg = list(map(float, msg.payload.decode().strip('][').split(',')))
                client.publish("home/Car/charging_wallbox_power", nrg[11])
                if car >= 0:
                    client.publish("home/Car/car_connected", int(car not in [0, 1, 5]))
            if topicParts[-1] == "modelStatus": modelStatus = int(msg.payload.decode())
            updatedAt = time.time()
        elif topicParts[1] == "inverter":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            wallbox(json.loads(msg.payload), client)
        elif topicParts[1] == "WallboxMode":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global wallboxMode
            wallboxMode = msg.payload.decode()
        elif topicParts[1] == "WallboxAmp":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global wallboxMaxAmp
            wallboxMaxAmp = int(msg.payload.decode())
        elif topicParts[1] == "WallboxStartSOC":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global wallboxStartSOC
            wallboxStartSOC = int(msg.payload.decode())
        elif topicParts[1] == "WallboxStopAtSOCDiff":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global wallboxStopAtSOCDiff
            wallboxStopAtSOCDiff = int(msg.payload.decode())
        elif topicParts[1] == "WallboxReserveAmp":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global amp_reserve
            amp_reserve = int(msg.payload.decode())

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    global amp, alw, frc, car, nrg, modelStatus, updatedAt
    for attempt in range(5):
        try:
            response = requests.get(wallboxConfig["address"] + 'api/status?filter=amp,alw,frc,car,nrg,modelStatus', timeout=10)
            res = json.loads(response.text)
            amp = res["amp"]
            alw = res["alw"]
            frc = res["frc"]
            car = res["car"]
            nrg = res["nrg"]
            modelStatus = res["modelStatus"]
            updatedAt = time.time()
            break
        except (JSONDecodeError, requests.exceptions.RequestException) as e:
            print(f"[wallbox] Error connecting to wallbox (attempt {attempt + 1}/5): {e}")
            if attempt < 4:
                time.sleep(10)
            else:
                print("[wallbox] Could not reach wallbox after 5 attempts, exiting")
                return
    client = connect_mqtt("wallbox3")
    subscribe(client, ["wallbox/inverter", "go-eCharger/201630/#", "command/WallboxMode", "command/WallboxAmp", "command/WallboxStartSOC", "command/WallboxStopAtSOCDiff", "command/WallboxReserveAmp"])
    print("[wallbox] Started")
    client.loop_forever()


if __name__ == '__main__':
    run()


def clean_data():
    global maxSocWhileCharging
    maxSocWhileCharging = 0