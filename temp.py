import time

import seeed_dht

import asyncio

from common import connect_mqtt, publishProperties


async def store_runtime_data():
    sensor = seeed_dht.DHT("11", 12)
    client = connect_mqtt("temp")
    client.loop_start()

    while True:
        humi, temp = sensor.read()

        client.publish("home/weather/sensors/temperature_in", temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/weather/sensors/humidity_in", humi, qos=2, properties=publishProperties).wait_for_publish()

        time.sleep(30)


asyncio.run(store_runtime_data())
