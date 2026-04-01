import json
import time as ttime
import traceback
from datetime import datetime, time, timedelta, timezone
from pprint import pprint

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from metno_locationforecast import Place, Forecast

from common import connect_mqtt, publishProperties
from config import generalConfig as c, influxConfig
from secret import influxToken

prdikov = Place("Malý Jeníkov", 49.15049, 15.23491, 578)
forecast = Forecast(prdikov, "Matej Pristak/1.0 matej.pristak@gmail.com", "compact")

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def publish(client):
    print("[yr] Started")
    while True:
        try:
            forecast.update()

            if (c["debug"]):
                pprint(forecast.data)
            d = datetime.today()
            d_min = datetime.combine(d, time.min)
            d_max = datetime.combine(d, time.max) + timedelta(hours=7)

            client.publish("home/weatherforecast/yr/maxtemp", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value, qos=2, properties=publishProperties).wait_for_publish()
            client.publish("home/weatherforecast/yr/mintemp", min(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value, qos=2, properties=publishProperties).wait_for_publish()
            client.publish("home/weatherforecast/yr/maxwind", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["wind_speed"].value).variables["wind_speed"].value * 3.6, qos=2, properties=publishProperties).wait_for_publish()
            client.publish("home/weatherforecast/yr/precip", sum(map(lambda x: x.variables["precipitation_amount"].value, forecast.data.intervals_between(d_min, d_max))), qos=2, properties=publishProperties).wait_for_publish()

            # Publish today's hourly forecast (full day, 00:00–23:59)
            today_start = datetime.combine(d, time.min)
            today_end = datetime.combine(d, time.max)
            hourly = {}
            for interval in forecast.data.intervals_between(today_start, today_end):
                hour_str = interval.start_time.strftime("%H:%M")
                temp_val = round(interval.variables["air_temperature"].value, 1)
                hourly[hour_str] = temp_val

                # Write each hour to InfluxDB with proper timestamp
                ts = interval.start_time.replace(tzinfo=timezone.utc)
                write_api.write(bucket=influxConfig["bucket"], record=Point("TempForecast").field("temperature", float(temp_val)).time(ts))

                # Publish individual hours to MQTT
                hour_key = interval.start_time.strftime("%H")
                client.publish(f"home/tempforecast/yr/{hour_key}", temp_val, qos=2, properties=publishProperties).wait_for_publish()

            # Publish JSON summary for other consumers
            client.publish("jsons/weatherforecast/yr/hourly", json.dumps(hourly), qos=2, properties=publishProperties).wait_for_publish()

            if datetime.now().hour == 23 and datetime.now().minute > 30:
                # tomorrow only
                d_min = datetime.combine(datetime.today(), time.max)
                d_max = datetime.combine(datetime.today(), time.max) + timedelta(hours=24)
                temps = {}
                for interval in forecast.data.intervals_between(d_min, d_max):
                    temps[interval.start_time.timestamp()] = interval.variables["air_temperature"].value

                client.publish("jsons/weatherforecast/yr/tomorrow", json.dumps(temps), qos=2, properties=publishProperties).wait_for_publish()
        except Exception as e:
            print(f"[yr] Error: {e}")
            traceback.print_exc()
        ttime.sleep(1800)


def run():
    client = connect_mqtt("yr")
    client.loop_start()
    publish(client)


if __name__ == '__main__':
    run()
