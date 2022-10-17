import time

import seeed_sgp30
from grove.i2c import Bus

import asyncio

from common import connect_mqtt


async def store_runtime_data():
    sgp30 = seeed_sgp30.grove_sgp30(Bus())
    client = connect_mqtt("co2")
    client.loop_start()

    while True:
        data = sgp30.read_measurements()
        co2_eq_ppm, tvoc_ppb = data.data

        client.publish("home/weather/sensors/co2", co2_eq_ppm)
        client.publish("home/weather/sensors/voc", tvoc_ppb)

        time.sleep(30)


asyncio.run(store_runtime_data())
