import asyncio
import threading
from datetime import datetime


from estia_api import ToshibaAcHttpApi

from paho.mqtt import client as mqtt_client
from common import connect_mqtt
from config import influxConfig
from secret import toshibaUsername, toshibaSecret, influxToken
from config import generalConfig as c, estiaConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# every 5 min, take the difference in used energy from Estia and calculate the updated COP

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret)
connected = False
heat_loss = 143 # W/K
temps = [18] * 24

def calculate_cop(today_usages: list, today_temp_avgs: list):
    if c["debug"]: print(f"today consumption: {today_usages},\ntemps: {today_temp_avgs}")

    cop = 0
    total_consumption = 0

    for hourly_temp, hourly_consumption in zip(today_temp_avgs, today_usages):
        if hourly_temp > 17 or hourly_consumption == 0:
            continue
        new_cop = (heat_loss * (18 - hourly_temp)) / hourly_consumption
        cop = (total_consumption * cop + hourly_consumption * new_cop) / (hourly_consumption + total_consumption)
        if c["debug"]: print(f"HOURLY: {hourly_temp}C   {hourly_consumption}Wh  -> COP {cop}")
        total_consumption += hourly_consumption

    if c["debug"]: print(f"COP: {cop}")
    return cop

async def calc():
    global connected, api

    await api.connect()
    await api.get_devices()

    while True:
        await asyncio.sleep(30)
        hourly_usage = (await api.get_hourly_consumption(estiaConfig["device_unique_id"], datetime.now()))[0]["EnergyConsumption"]
        if hourly_usage is not None: # polnoc
            energy_values = [item["Energy"] for item in hourly_usage]
            cop = calculate_cop(energy_values, temps)
            write_api.write(bucket=influxConfig["bucket"], record=Point("Estia").field("cop", cop))

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(calc())
    loop.close()

def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        global temps
        payload = msg.payload.decode()
        if c["debug"]: print(f"Received `{payload}` from `{msg.topic}` topic")
        temps[datetime.now().hour] = float(payload)

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt("estia_energy2")
    subscribe(client, ["home/weather/local/temperature"])
    threading.Thread(target=start_async_loop, daemon=True).start()
    client.loop_forever()

if __name__ == '__main__':
    run()
