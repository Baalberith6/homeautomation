import asyncio
import sys
import traceback
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

from carconnectivity import carconnectivity

from common import connect_mqtt, publishProperties
from config import skodaConfig
from secret import carConnectivityConfig


def calculate_charging_time_remaining(vehicle):
    """Calculate remaining charging time in minutes from estimated completion date"""
    if vehicle.charging.power.value > 0:
        estimated_completion = vehicle.charging.estimated_date_reached.value
        if estimated_completion:
            now = datetime.now(estimated_completion.tzinfo)  # Use same timezone
            return max(0, int((estimated_completion - now).total_seconds() / 60))
    return None


async def main():
    client = connect_mqtt("skoda")
    client.loop_start()

    car_connectivity = None
    try:
        car_connectivity = carconnectivity.CarConnectivity(config=carConnectivityConfig)
        print("[skoda] Started")

        while True:
            try:
                print("[skoda] Fetching vehicle data...")
                car_connectivity.fetch_all()  # Refresh vehicle data
                garage = car_connectivity.get_garage()
                for vehicle in garage.list_vehicles():
                    if vehicle.vin.value == skodaConfig["vin_skoda"]:
                        soc = vehicle.drives.drives["primary"].level.value
                        range_km = vehicle.drives.total_range.value
                        client.publish("home/Car/battery_level_enyaq", soc, qos=2, properties=publishProperties).wait_for_publish()

                        time_remaining = calculate_charging_time_remaining(vehicle)
                        if time_remaining is not None:
                            client.publish("home/Car/charging_time_left", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                        client.publish("home/Car/electric_range_enyaq", range_km, qos=2, properties=publishProperties).wait_for_publish()
                        print(f"[skoda] Enyaq: SOC={soc}%, range={range_km}km")
                    if vehicle.vin.value == skodaConfig["vin_vw"]:
                        soc = vehicle.drives.drives["primary"].level.value
                        range_km = vehicle.drives.total_range.value
                        client.publish("home/Car/battery_level_vw", soc, qos=2, properties=publishProperties).wait_for_publish()

                        time_remaining = calculate_charging_time_remaining(vehicle)
                        if time_remaining is not None:
                            client.publish("home/Car/charging_time_left", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                        client.publish("home/Car/electric_range_vw", range_km, qos=2, properties=publishProperties).wait_for_publish()
                        print(f"[skoda] VW: SOC={soc}%, range={range_km}km")
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
