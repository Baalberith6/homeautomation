import asyncio
from datetime import datetime

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
        print('Connecting')
        car_connectivity.fetch_all()
        garage = car_connectivity.get_garage()

        while True:
            for vehicle in garage.list_vehicles():
                if vehicle.vin.value == skodaConfig["vin_skoda"]:
                    client.publish("home/Car/battery_level_enyaq", vehicle.drives.drives["primary"].level.value, qos=2, properties=publishProperties).wait_for_publish()

                    time_remaining = calculate_charging_time_remaining(vehicle)
                    if time_remaining is not None:
                        client.publish("home/Car/charging_time_left", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                    client.publish("home/Car/electric_range_enyaq", vehicle.drives.total_range.value, qos=2, properties=publishProperties).wait_for_publish()
                if vehicle.vin.value == skodaConfig["vin_vw"]:
                    client.publish("home/Car/battery_level_vw", vehicle.drives.drives["primary"].level.value, qos=2, properties=publishProperties).wait_for_publish()

                    time_remaining = calculate_charging_time_remaining(vehicle)
                    if time_remaining is not None:
                        client.publish("home/Car/charging_time_left", time_remaining, qos=2, properties=publishProperties).wait_for_publish()

                    client.publish("home/Car/electric_range_vw", vehicle.drives.total_range.value, qos=2, properties=publishProperties).wait_for_publish()

            await asyncio.sleep(120)
    except Exception as e:
        print(f'Error happened: {e}')
    finally:
        # Closing connection
        if car_connectivity:
            car_connectivity.shutdown()
        print('Disconnecting')


if __name__ == "__main__":
    asyncio.run(main())
