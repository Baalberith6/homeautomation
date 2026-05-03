import asyncio
import json
import sys
import time
import urllib.request
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

from carconnectivity import carconnectivity  # noqa: E402
from carconnectivity.charging import Charging  # noqa: E402
from carconnectivity.charging_connector import ChargingConnector  # noqa: E402
from carconnectivity.command_impl import WakeSleepCommand  # noqa: E402
from carconnectivity.vehicle import GenericVehicle  # noqa: E402

from common import connect_mqtt, publishProperties  # noqa: E402
from config import skodaConfig  # noqa: E402
from secret import carConnectivityConfig  # noqa: E402


def is_charging(vehicle):
    """Check if vehicle is actually charging (not stale cached data)"""
    if vehicle.charging.state.value != Charging.ChargingState.CHARGING:
        return False
    # Car stays online while charging; offline means stale cached state
    if vehicle.connection_state.value == GenericVehicle.ConnectionState.OFFLINE:
        return False
    # Zero power means not actually charging — manufacturer may report
    # stale CHARGING state after charging stops
    power = vehicle.charging.power.value
    if power is not None and power <= 0:
        return False
    return True


def is_plug_connected(vehicle):
    """Check if the charging cable is physically plugged in."""
    state = vehicle.charging.connector.connection_state.value
    return state == ChargingConnector.ChargingConnectorConnectionState.CONNECTED


def calculate_charging_time_remaining(vehicle):
    """Calculate remaining charging time in minutes from estimated completion date"""
    if not is_charging(vehicle):
        return 0
    estimated_completion = vehicle.charging.estimated_date_reached.value
    if estimated_completion:
        now = datetime.now(estimated_completion.tzinfo)
        return max(0, int((estimated_completion - now).total_seconds() / 60))
    return 0


FETCH_TIMEOUT = 60  # seconds — kill and retry if fetch_all() hangs
WAKE_INTERVAL_SECONDS = 300  # force-refresh cadence while charging

_geo_cache = {}
_last_wake = {}  # VIN -> monotonic timestamp of last wake command


def maybe_wake(vehicle):
    """Send WAKE while charging to force fresh backend status.

    Why: VW/Skoda backends only refresh from a parked, charging car
    ~every 10 min, so polling alone yields stale SoC/power data.
    """
    if not is_charging(vehicle):
        return
    cmds = vehicle.commands.commands if vehicle.commands else {}
    wake_cmd = cmds.get("wake-sleep")
    if wake_cmd is None:
        return
    vin = vehicle.vin.value
    now = time.monotonic()
    if now - _last_wake.get(vin, 0) < WAKE_INTERVAL_SECONDS:
        return
    try:
        wake_cmd.value = WakeSleepCommand.Command.WAKE
        _last_wake[vin] = now
        print(f"[skoda] Wake sent for ...{vin[-6:]}")
    except Exception as e:
        print(f"[skoda] Wake failed for ...{vin[-6:]}: {str(e)[:160]}")


def get_address(lat, lon):
    """Reverse geocode lat/lon to short address via Nominatim."""
    key = (round(lat, 3), round(lon, 3))
    if key in _geo_cache:
        return _geo_cache[key]
    try:
        url = (f"https://nominatim.openstreetmap.org/reverse"
               f"?lat={lat}&lon={lon}&format=json&addressdetails=1")
        req = urllib.request.Request(
            url, headers={"User-Agent": "homeautomation/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        a = data.get("address", {})
        road = a.get("road", "")
        house = a.get("house_number", "")
        suburb = (a.get("suburb") or a.get("quarter")
                  or a.get("city_district")
                  or a.get("neighbourhood", ""))
        city = (a.get("city") or a.get("town")
                or a.get("village", ""))
        parts = []
        if road:
            parts.append(f"{road} {house}".strip() if house else road)
        if suburb and suburb != city:
            parts.append(suburb)
        if city:
            parts.append(city)
        result = ", ".join(parts) if parts else ""
        _geo_cache[key] = result
        return result
    except Exception as e:
        print(f"[skoda] Geocode error: {e}")
        return ""


async def main():
    client = connect_mqtt("skoda5")
    client.loop_start()

    car_connectivity = None
    try:
        car_connectivity = carconnectivity.CarConnectivity(config=carConnectivityConfig)
        print("[skoda] Started")

        loop = asyncio.get_event_loop()
        while True:
            try:
                print("[skoda] Fetching vehicle data...")
                await asyncio.wait_for(
                    loop.run_in_executor(None, car_connectivity.fetch_all),
                    timeout=FETCH_TIMEOUT
                )
                garage = car_connectivity.get_garage()
                for vehicle in garage.list_vehicles():
                    if vehicle.vin.value == skodaConfig["vin_skoda"]:
                        soc = vehicle.drives.drives["primary"].level.value
                        range_km = vehicle.drives.total_range.value
                        client.publish("home/Car/battery_level_enyaq", soc, qos=2, properties=publishProperties).wait_for_publish()

                        time_remaining = calculate_charging_time_remaining(vehicle)
                        client.publish("home/Car/charging_time_left_enyaq", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                        client.publish("home/Car/electric_range_enyaq", range_km, qos=2, properties=publishProperties).wait_for_publish()

                        plug = is_plug_connected(vehicle)
                        client.publish("home/Car/plug_connected_enyaq", int(plug), qos=2, properties=publishProperties).wait_for_publish()

                        try:
                            target_soc = vehicle.charging.settings.target_level.value
                        except (AttributeError, KeyError):
                            target_soc = None
                        if target_soc is not None:
                            client.publish("home/Car/target_soc_enyaq", int(target_soc), qos=2, properties=publishProperties).wait_for_publish()

                        try:
                            lat = float(vehicle.position.latitude.value)
                            lon = float(vehicle.position.longitude.value)
                        except (AttributeError, TypeError, ValueError):
                            lat = None
                            lon = None
                        address = ""
                        if lat is not None and lon is not None:
                            client.publish("home/Car/lat_enyaq", lat, qos=2, properties=publishProperties).wait_for_publish()
                            client.publish("home/Car/lon_enyaq", lon, qos=2, properties=publishProperties).wait_for_publish()
                            address = get_address(lat, lon)
                        if address:
                            client.publish("diag/Car/address_enyaq", address, qos=2, properties=publishProperties).wait_for_publish()

                        charging_state = vehicle.charging.state.value
                        print(f"[skoda] Enyaq: SOC={soc}%, range={range_km}km, charging={charging_state}, plug={'Y' if plug else 'N'}, time_left={time_remaining}min, target={target_soc}, addr={address}")
                        maybe_wake(vehicle)
                    if vehicle.vin.value == skodaConfig["vin_vw"]:
                        soc = vehicle.drives.drives["primary"].level.value
                        range_km = vehicle.drives.total_range.value
                        client.publish("home/Car/battery_level_vw", soc, qos=2, properties=publishProperties).wait_for_publish()

                        time_remaining = calculate_charging_time_remaining(vehicle)
                        client.publish("home/Car/charging_time_left_vw", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                        client.publish("home/Car/electric_range_vw", range_km, qos=2, properties=publishProperties).wait_for_publish()

                        plug = is_plug_connected(vehicle)
                        client.publish("home/Car/plug_connected_vw", int(plug), qos=2, properties=publishProperties).wait_for_publish()

                        try:
                            target_soc = vehicle.charging.settings.target_level.value
                        except (AttributeError, KeyError):
                            target_soc = None
                        if target_soc is not None:
                            client.publish("home/Car/target_soc_vw", int(target_soc), qos=2, properties=publishProperties).wait_for_publish()

                        try:
                            lat = float(vehicle.position.latitude.value)
                            lon = float(vehicle.position.longitude.value)
                        except (AttributeError, TypeError, ValueError):
                            lat = None
                            lon = None
                        address = ""
                        if lat is not None and lon is not None:
                            client.publish("home/Car/lat_vw", lat, qos=2, properties=publishProperties).wait_for_publish()
                            client.publish("home/Car/lon_vw", lon, qos=2, properties=publishProperties).wait_for_publish()
                            address = get_address(lat, lon)
                        if address:
                            client.publish("diag/Car/address_vw", address, qos=2, properties=publishProperties).wait_for_publish()

                        charging_state = vehicle.charging.state.value
                        print(f"[skoda] VW: SOC={soc}%, range={range_km}km, charging={charging_state}, plug={'Y' if plug else 'N'}, time_left={time_remaining}min, target={target_soc}, addr={address}")
                        maybe_wake(vehicle)
            except asyncio.TimeoutError:
                print(f"[skoda] fetch_all() timed out after"
                      f" {FETCH_TIMEOUT}s, reconnecting...")
                try:
                    car_connectivity.shutdown()
                except Exception:
                    pass
                car_connectivity = carconnectivity.CarConnectivity(
                    config=carConnectivityConfig)
                print("[skoda] Reconnected")
            except Exception as e:
                error_msg = str(e)[:200]
                print(f"[skoda] Error: {error_msg}")
            await asyncio.sleep(120)
    finally:
        if car_connectivity:
            car_connectivity.shutdown()
        print('[skoda] Disconnecting')


if __name__ == "__main__":
    asyncio.run(main())
