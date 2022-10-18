import time

import seeed_sgp30
from grove.i2c import Bus

import asyncio

from common import connect_mqtt, publishProperties


async def store_runtime_data():
    sgp30 = seeed_sgp30.grove_sgp30(Bus())
    client = connect_mqtt("co2")
    client.loop_start()

    while True:
        data = sgp30.read_measurements()
        co2_eq_ppm, tvoc_ppb = data.data

        client.publish("home/weather/sensors/co2", co2_eq_ppm, qos=2, properties=publishProperties)
        client.publish("home/weather/sensors/voc", tvoc_ppb, qos=2, properties=publishProperties)

        time.sleep(5)


asyncio.run(store_runtime_data())
