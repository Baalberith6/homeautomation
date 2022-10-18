import asyncio
import time

from aiohttp import ClientSession
from skodaconnect import Connection

from common import connect_mqtt, publishProperties
from secret import skodaMail, skodaPassword


async def main():
    client = connect_mqtt("skoda")
    client.loop_start()

    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = Connection(session, skodaMail, skodaPassword, "false")
        await connection.doLogin()
        await connection.get_vehicles()
        while True:
            await connection.update_all()
            for instrument in connection.vehicles[0].dashboard(mutable=False).instruments:
                if instrument.attr == "battery_level":
                    client.publish("home/Car/battery_level", instrument.state, qos=2, properties=publishProperties)
                if instrument.attr == "charging_time_left":
                    hour, min = instrument.state.split(":")
                    client.publish("home/Car/charging_time_left", float(hour) * 60 + float(min), qos=2, properties=publishProperties)
                if instrument.attr == "electric_range":
                    client.publish("home/Car/electric_range", instrument.state, qos=2, properties=publishProperties)
                if instrument.attr == "charging_power":
                    client.publish("home/Car/charging_power", instrument.state, qos=2, properties=publishProperties)

            time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())