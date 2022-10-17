import time

import seeed_dht

import asyncio

from common import connect_mqtt


async def store_runtime_data():
    sensor = seeed_dht.DHT("11", 12)
    client = connect_mqtt("temp")
    client.loop_start()

    while True:
        humi, temp = sensor.read()

        client.publish("home/weather/sensors/temperature_in", temp)
        client.publish("home/weather/sensors/humidity_in", humi)

        time.sleep(30)


asyncio.run(store_runtime_data())
