from pprint import pprint
from config import wundergroundConfig, influxConfig

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from wunderground_pws import WUndergroundAPI, units

wu = WUndergroundAPI(
    api_key=wundergroundConfig["apiKey"],
    default_station_id=wundergroundConfig["stationId"],
    units=units.METRIC_UNITS,
)

w = wu.current()["observations"][0]

# pprint(w)

client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
write_api = client.write_api(write_options=SYNCHRONOUS)

write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("humidity", w["humidity"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("temperature", w["metric"]["temp"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windChill", w["metric"]["windChill"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windSpeed", w["metric"]["windSpeed"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windGust", w["metric"]["windGust"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("precipRate", w["metric"]["precipRate"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("precipTotal", w["metric"]["precipTotal"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("solarRadiation", w["solarRadiation"]))
write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("winddir", w["winddir"]))
