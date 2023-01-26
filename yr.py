import json
import time as ttime
from datetime import datetime, time, timedelta
from pprint import pprint

from metno_locationforecast import Place, Forecast

from common import connect_mqtt, publishProperties
from config import generalConfig as c

prdikov = Place("Malý Jeníkov", 49.15049, 15.23491, 578)
forecast = Forecast(prdikov, "Matej Pristak/1.0 matej.pristak@gmail.com", "compact")


def publish(client):
    while True:
        forecast.update()

        if (c["debug"]):
            pprint (forecast.data)
        d = datetime.today()
        d_min = datetime.combine(d, time.min)
        d_max = datetime.combine(d, time.max) + timedelta(hours=7)

        client.publish("home/weatherforecast/yr/maxtemp", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/weatherforecast/yr/mintemp", min(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/weatherforecast/yr/maxwind", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["wind_speed"].value).variables["wind_speed"].value * 3.6, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/weatherforecast/yr/precip", sum(map(lambda x: x.variables["precipitation_amount"].value, forecast.data.intervals_between(d_min, d_max))), qos=2, properties=publishProperties).wait_for_publish()

        if datetime.now().hour == 23 and datetime.now().minute > 30:
            # tomorrow only
            d_min = datetime.combine(datetime.today(), time.max)
            d_max = datetime.combine(datetime.today(), time.max) + timedelta(hours=24)
            temps = {}
            for interval in forecast.data.intervals_between(d_min, d_max):
                temps[interval.start_time.timestamp()] = interval.variables["air_temperature"].value

            client.publish("jsons/weatherforecast/yr/tomorrow", json.dumps(temps), qos=2, properties=publishProperties).wait_for_publish()

        ttime.sleep(1800)


def run():
    client = connect_mqtt("yr2")
    client.loop_start()
    publish(client)


if __name__ == '__main__':
    run()
