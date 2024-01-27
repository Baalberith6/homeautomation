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

hour_calculated = datetime.now().hour - 1
cop = 0
temp = 0
api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret)
connected = False
heat_loss = 143 # W/K

def calculate_cop(today_usage: int, last_hour_usage: int, old_cop: float, temp: float):
    if c["debug"]: print(f"today: {today_usage}, last hour: {last_hour_usage}, old_cop: {old_cop}, temp: {temp}")
    if temp > 17:
        return old_cop

    new_cop = (heat_loss * (18 - temp)) / last_hour_usage
    return (today_usage * old_cop + last_hour_usage * new_cop) / (today_usage + last_hour_usage)

async def calc():
    global connected, cop, api, temp, hour_calculated

    await api.connect()
    await api.get_devices()

    while True:
        await asyncio.sleep(300)
        if hour_calculated != datetime.now().hour:
            hourly_usage = (await api.get_hourly_consumption(estiaConfig["device_unique_id"], datetime.now()))[0]["EnergyConsumption"]
            last_hour_usage = hourly_usage[hour_calculated]["Energy"]
            today_usage = 0
            for hourly in hourly_usage:
                if int(hourly["Time"]) == hour_calculated:
                    break
                today_usage += hourly["Energy"]
            cop = calculate_cop(last_hour_usage, today_usage, cop, float(temp))
            if c["debug"]: print(f"COP: {cop}, last hour used: {last_hour_usage}Wh, today_usage: {today_usage}Wh")
            write_api.write(bucket=influxConfig["bucket"], record=Point("Estia").field("cop", cop))
            hour_calculated = datetime.now().hour
            if hour_calculated == 0:
                cop = 0

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(calc())
    loop.close()

def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        global temp
        payload = msg.payload.decode()
        if c["debug"]: print(f"Received `{payload}` from `{msg.topic}` topic")
        temp = float(payload)

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt("estia_energy")
    subscribe(client, ["home/weather/local/temperature"])
    threading.Thread(target=start_async_loop, daemon=True).start()
    client.loop_forever()

if __name__ == '__main__':
    run()
