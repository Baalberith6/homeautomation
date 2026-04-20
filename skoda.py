import asyncio
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

from carconnectivity import carconnectivity  # noqa: E402
from carconnectivity.charging import Charging  # noqa: E402
from carconnectivity.charging_connector import ChargingConnector  # noqa: E402
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

                        charging_state = vehicle.charging.state.value
                        print(f"[skoda] Enyaq: SOC={soc}%, range={range_km}km, charging={charging_state}, plug={'Y' if plug else 'N'}, time_left={time_remaining}min, target={target_soc}")
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

                        charging_state = vehicle.charging.state.value
                        print(f"[skoda] VW: SOC={soc}%, range={range_km}km, charging={charging_state}, plug={'Y' if plug else 'N'}, time_left={time_remaining}min, target={target_soc}")
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
