import time

import seeed_sgp30
from grove.i2c import Bus

import asyncio

from config import influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


async def store_runtime_data():
    sgp30 = seeed_sgp30.grove_sgp30(Bus())
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        data = sgp30.read_measurements()
        co2_eq_ppm, tvoc_ppb = data.data

        write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("co2", co2_eq_ppm))

        time.sleep(30)


asyncio.run(store_runtime_data())
