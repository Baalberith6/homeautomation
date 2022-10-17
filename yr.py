import time as ttime
from datetime import datetime, time, timedelta

from metno_locationforecast import Place, Forecast

from common import connect_mqtt


prdikov = Place("Malý Jeníkov", 49.15049, 15.23491, 578)
forecast = Forecast(prdikov, "Matej Pristak/1.0 matej.pristak@gmail.com", "compact")


def publish(client):
    while True:
        forecast.update()

        d = datetime.today()
        d_min = datetime.combine(d, time.min)
        d_max = datetime.combine(d, time.max) + timedelta(hours=7)

        client.publish("home/weather/forecast/yr/maxtemp", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value)
        client.publish("home/weather/forecast/yr/mintemp", min(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value)
        client.publish("home/weather/forecast/yr/maxwind", max(forecast.data.intervals_between(d_min, d_max), key=lambda x: x.variables["wind_speed"].value).variables["wind_speed"].value * 3.6)
        client.publish("home/weather/forecast/yr/precip", sum(map(lambda x: x.variables["precipitation_amount"].value, forecast.data.intervals_between(d_min, d_max))))
        ttime.sleep(1800)


def run():
    client = connect_mqtt("yr")
    client.loop_start()
    publish(client)


if __name__ == '__main__':
    run()
