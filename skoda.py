import asyncio
import time

from aiohttp import ClientSession
from skodaconnect import Connection

from config import skodaConfig, influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


async def main():
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)
    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = Connection(session, skodaConfig["username"], skodaConfig["password"], "false")
        await connection.doLogin()
        await connection.get_vehicles()
        for instrument in connection.vehicles[0].dashboard(mutable=False).instruments:
            if (instrument.attr == "battery_level"):
                write_api.write(bucket=influxConfig["bucket"], record=Point("Car").field("battery_level", instrument.state))
            if (instrument.attr == "charging_time_left"):
                write_api.write(bucket=influxConfig["bucket"], record=Point("Car").field("charging_time_left", instrument.state))
            if (instrument.attr == "electric_range"):
                write_api.write(bucket=influxConfig["bucket"], record=Point("Car").field("electric_range", instrument.state))
            if (instrument.attr == "charging_power"):
                write_api.write(bucket=influxConfig["bucket"], record=Point("Car").field("charging_power", instrument.state))

while True:
    if __name__ == "__main__":
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    time.sleep(600)