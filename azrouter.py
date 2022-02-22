import asyncio
import time
from pprint import pprint

import requests

from config import azrouterConfig, influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


def _request(path: tuple):
    """Forward a raw request to Weather Underground APIs"""
    r = requests.get(azrouterConfig["ip_address"] + '/'.join(path))
    return r.json()


async def store_runtime_data():
    r = _request(("api", "v1", "power"))

    # pprint(r)

    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").tag("sum", "today").field("saved_energy", r["output"]["energy"][4]["value"]))
    write_api.write(bucket=influxConfig["bucket"], record=Point("FVE").field("saved_energy", r["output"]["power"][0]["value"]))

asyncio.run(store_runtime_data())
    # time.sleep(15)
