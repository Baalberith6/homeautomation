import time

import seeed_dht

import asyncio

from config import influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

async def store_runtime_data():
    sensor = seeed_dht.DHT("11", 12)
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        humi, temp = sensor.read()

        write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("temperature_in", temp))
        write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("humidity_in", humi))

        time.sleep(30)


asyncio.run(store_runtime_data())
