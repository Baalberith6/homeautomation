import math
import json
from json import JSONDecodeError

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
def calculate_current(inverter, actual_charging_current: int, car_phases: int):
    # kanvica do bat - 1900 pgrid2, 1900 backup_p2
    # bat na 1.9 - pgrid 3x 1000 + 3000 active p
    # traktor a bat - load_p1 1450, 1650 active, 1900 bat, 5700 tot, total_inverter_power = 3491 W
    # max 9000 / 3 per phase

    stop_at = 6  # Amp
    start_at = 6
    max_amp = 15
    should_charge = True
    was_charging = actual_charging_current != 0

    # max_i1 = max_amp - (inverter["load_p1"] / 230 + inverter["backup_i1"])
    # max_i2 = max_amp - (inverter["load_p2"] / 230 + inverter["backup_i2"])
    # max_i3 = max_amp - (inverter["load_p3"] / 230 + inverter["backup_i3"])
    # max_possible_current = min(max_i1, max_i2, max_i3)
    # available_current = min(max_possible_current,
    #                         (inverter["ppv"] / 690 - inverter["house_consumption"] / 690))  # 230 * 3
    # allowable_current = actual_charging_current + available_current - 0.2  # 0.2A min. reserve due to inverter loses, car charges 0.5A below
    # allowable_current_capped = math.floor(min(max_amp - 1, max(stop_at, allowable_current)))  # step down by 1A
    # would_add = (allowable_current - actual_charging_current)

    # 2-phase check
    # while allowable_current_capped >= stop_at and ((allowable_current_capped * car_phases * 230) + ((math.floor(max_amp) - allowable_current_capped) * 690)) < inverter["ppv"]:
    #     allowable_current_capped = allowable_current_capped - 1
    #     if allowable_current_capped < stop_at and inverter["battery_soc"] < 100:  # if ppv over 8200W and battery is 100, we would hit limit
    #         allowable_current_capped = stop_at
    #         break

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


async def wallbox(inverter):
    try:
        response = req.get(wallboxConfig["address"] + 'api/status?filter=amp,alw,frc,car,nrg,modelstatus')
        res = json.loads(response.text)
    except JSONDecodeError:
        if c["debug"]: print("Wallbox is OFFLINE")
        return

    phases = 0
    if res["nrg"][4] > 1: phases += 1
    if res["nrg"][5] > 1: phases += 1
    if res["nrg"][6] > 1: phases += 1
    if phases != 1: phases = 3  # we don't know the number of connected phases before starting, also safe-default to 3 except when 1
    if c["debug"]: print(f"phases: {phases}")

    if res["car"] in [0, 1, 5]:
        if c["debug"]: print(f"no charge allowed - perhaps car not connected or doesn't want to charge, car state {res['car']}")
        if res["frc"] != 1:
            if c["debug"]: print("setting force state to disabled")
            req.get(wallboxConfig["address"] + 'api/set?frc=1')
        return  # no charge allowed - perhaps car not connected, doesn't want to charge or disabled in app?
    if res["modelStatus"] == 22:
        if c["debug"]: print("NotChargingBecauseSimulateUnplugging")
        return  # NotChargingBecauseSimulateUnplugging
    previous_charging_curr = res["amp"] if res["frc"] == 0 and res["car"] != 4 else 0  # if charging allowed and already charging

    charging_curr = calculate_current(inverter, previous_charging_curr, phases)

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
