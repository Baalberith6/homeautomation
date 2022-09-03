import math
import json
import requests as req

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
    available_current = min(max_possible_current,
                            (inverter["ppv"] / 690 - inverter["house_consumption"] / 690))  # 230 * 3
    allowable_current = actual_charging_current + available_current - 0.2  # 345W min. reserve
    allowable_current_capped = min(max_amp - 1, max(stop_at, math.floor(allowable_current)))  # step down by 1A
    would_add = (allowable_current - actual_charging_current)

    if was_charging:
        should_charge = allowable_current >= stop_at or inverter["battery_soc"] >= 80
        if c["debug"]: print(f"if charging, would charge: {should_charge}, {allowable_current_capped} A")

    if not was_charging:
        should_charge = allowable_current >= start_at and inverter["battery_soc"] > 95
        if c["debug"]: print(f"if NOT charging, would charge: {should_charge}, {allowable_current_capped} A")

    if c["debug"]: print(f"P1 avail {max_i1} A")
    if c["debug"]: print(f"P2 avail {max_i2} A")
    if c["debug"]: print(f"P3 avail {max_i3} A")
    if c["debug"]: print(f"PPV {inverter['ppv']} W")
    if c["debug"]: print(f"max {max_possible_current} A")
    if c["debug"]: print(f"avail {available_current} A")
    if c["debug"]: print(f"allowable {allowable_current} A")
    if c["debug"]: print(f"actual charging current {actual_charging_current} A")

    # print(f"would add {would_add} A")

    if not should_charge:
        return 0
    else:
        return allowable_current_capped


async def wallbox(inverter):
    response = req.get(wallboxConfig["address"] + 'api/status?filter=amp,alw,frc,car')
    res = json.loads(response.text)
    if res["car"] in [0, 1, 5]:
        if c["debug"]: print(f"no charge allowed - perhaps car not connected or doesn't want to charge, car state {res['car']}")
        if res["frc"] != 1:
            if c["debug"]: print("setting force state to disabled")
            req.get(wallboxConfig["address"] + 'api/set?frc=1')
        return  # no charge allowed - perhaps car not connected, doesn't want to charge or disabled in app?
    previous_charging_curr = res["amp"] if res["frc"] == 0 and res["car"] != 4 else 0 # if charging allowed and already charging

    charging_curr = calculate_current(inverter, previous_charging_curr)

    if res["frc"] == 1 and charging_curr > 0:  # stopped, but should start
        if c["debug"]: print(f"stopped, but should start, {charging_curr}A")
        req.get(wallboxConfig["address"] + 'api/set?amp={charging_curr}&frc=0')
    if res["frc"] == 0 and charging_curr > 0:  # started, just change amp
        if res["amp"] == charging_curr:
            if c["debug"]: print(f"started, do nothing, {charging_curr}A")
            return
        #       do nothing
        else:
            if c["debug"]: print(f"started, just change amp, {charging_curr}A")
            req.get(f'{wallboxConfig["address"]}api/set?amp={charging_curr}')
    if res["frc"] == 1 and charging_curr == 0:  # stopped, shouldn't start
        if c["debug"]: print(f"stopped, shouldn't start, {charging_curr}A")
        return
        # do nothing
    if res["frc"] == 0 and charging_curr == 0:  # started, should stop
        if c["debug"]: print(f"started, should stop, {charging_curr}A")
        req.get(wallboxConfig["address"] + 'api/set?frc=1')


test_data = {
    "ppv": 7641,
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
# inv = await goodwe.connect(inverterConfig["ip_address"])
# runtime_data = await inv.read_runtime_data()
# asyncio.run(wallbox(runtime_data))
# time.sleep(15)
