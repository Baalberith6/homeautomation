import asyncio
import time
from datetime import datetime, timedelta
from pprint import pprint
from config import influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from metno_locationforecast import Place, Forecast


async def store_runtime_data():
    prdikov = Place("Malý Jeníkov", 49.15049, 15.23491, 578)
    forecast = Forecast(prdikov, "Matej Pristak/1.0 matej.pristak@gmail.com", "compact")
    forecast.update()

    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # print(forecast)
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "today")
                    .field("maxtemp",
                           max(forecast.data.intervals_between(datetime.today(), datetime.today() + timedelta(days=1)),
                               key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "today")
                    .field("mintemp",
                           min(forecast.data.intervals_between(datetime.today(), datetime.today() + timedelta(days=1)),
                               key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "today")
                    .field("maxwind",
                           max(forecast.data.intervals_between(datetime.today(), datetime.today() + timedelta(days=1)),
                               key=lambda x: x.variables["wind_speed"].value).variables["wind_speed"].value * 3.6))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "today")
                    .field("precip",
                           sum(map(lambda x: x.variables["precipitation_amount"].value,
                                   forecast.data.intervals_between(datetime.today(),
                                                                   datetime.today() + timedelta(days=1))))))

    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "tomorrow")
                    .field("maxtemp",
                           max(forecast.data.intervals_between(datetime.today() + timedelta(days=1),
                                                               datetime.today() + timedelta(days=2)),
                               key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "tomorrow")
                    .field("mintemp",
                           min(forecast.data.intervals_between(datetime.today() + timedelta(days=1),
                                                               datetime.today() + timedelta(days=2)),
                               key=lambda x: x.variables["air_temperature"].value).variables["air_temperature"].value))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "tomorrow")
                    .field("maxwind",
                           max(forecast.data.intervals_between(datetime.today() + timedelta(days=1),
                                                               datetime.today() + timedelta(days=2)),
                               key=lambda x: x.variables["wind_speed"].value).variables["wind_speed"].value * 3.6))
    write_api.write(bucket=influxConfig["bucket"], record=Point("WeatherForecast")
                    .tag("day", "tomorrow")
                    .field("precip",
                           sum(map(lambda x: x.variables["precipitation_amount"].value,
                                   forecast.data.intervals_between(datetime.today() + timedelta(days=1),
                                                                   datetime.today() + timedelta(days=2))))))

asyncio.run(store_runtime_data())
    # time.sleep(1800)
