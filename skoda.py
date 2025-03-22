import asyncio
import time

from aiohttp import ClientSession
from myskoda import MySkoda

from common import connect_mqtt, publishProperties
from config import skodaConfig
from secret import skodaMail, skodaPassword


async def main():
    client = connect_mqtt("skoda")
    client.loop_start()

    try:
        session = ClientSession()
        myskoda = MySkoda(session)
        print('Connecting')
        await myskoda.connect(skodaMail, skodaPassword)

        while True:
            charging = await myskoda.get_charging(skodaConfig["vin"])
            client.publish("home/Car/battery_level", charging.status.battery.state_of_charge_in_percent, qos=2, properties=publishProperties).wait_for_publish()
            client.publish("home/Car/charging_time_left", charging.status.remaining_time_to_fully_charged_in_minutes, qos=2, properties=publishProperties).wait_for_publish()
            client.publish("home/Car/electric_range", charging.status.battery.remaining_cruising_range_in_meters/1000, qos=2, properties=publishProperties).wait_for_publish()

            await asyncio.sleep(120)
    except:
        print('Error happened')
    finally:
        # Closing connection
        await myskoda.disconnect()
        print('Disconnecting')
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
