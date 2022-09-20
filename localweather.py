from flask import Flask, request
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from config import generalConfig as c, influxConfig

api = Flask(__name__)


@api.route('/weather', methods=['GET'])
def get_weather():
    temp = round((request.args.get('tempf', type=float) - 32) / 2)  # F -> C
    windchill = round((request.args.get('windchillf', type=float) - 32) / 2)  # F -> C
    humidity = request.args.get('humidity')  # %
    windspeed = round(request.args.get('windspeedmph', type=float) * 1.61, 2)  # mph -> kmh
    windgust = round(request.args.get('windgustmph', type=float) * 1.61, 2)  # mph -> kmh
    rain = round(request.args.get('rainin', type=float) * 25.4, 2)  # in -> cm
    dailyrain = round(request.args.get('dailyrainin', type=float) * 25.4, 2)  # in -> cm
    solarradiation = request.args.get('solarradiation', type=float)

    if c["debug"]:
        print(f"temp: {temp} C")
        print(f"windchill: {windchill} C")
        print(f"humidity: {humidity} %")
        print(f"windspeed: {windspeed} km/h")
        print(f"windgust: {windgust} km/h")
        print(f"rain: {rain} mm")
        print(f"dailyrain: {dailyrain} mm")
        print(f"solarradiation: {solarradiation} *")

    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("humidity", humidity))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("temperature", temp))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windChill", windchill))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windSpeed", windspeed))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("windGust", windgust))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("precipRate", rain))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("precipTotal", dailyrain))
    write_api.write(bucket=influxConfig["bucket"], record=Point("Weather").field("solarRadiation", solarradiation))

    return 'OK'


if __name__ == '__main__':
    api.run(host="0.0.0.0", port=5005)
