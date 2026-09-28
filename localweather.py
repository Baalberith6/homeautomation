import json
import logging, re
from datetime import datetime

from flask import Flask, request

from config import generalConfig as c
from common import connect_mqtt

api = Flask(__name__)


class SkipWeather200(logging.Filter):
    _pat = re.compile(r'"[A-Z]+ /weather(?:\?| )')

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not (self._pat.search(msg) and ' 200 ' in msg)


logging.getLogger('werkzeug').addFilter(SkipWeather200())

client = connect_mqtt("localweather")

temps_24h = [0.0] * 24


@api.route('/weather', methods=['GET'])
def get_weather():
    temp = round((request.args.get('tempf', type=float) - 32) / 1.8, 2)  # F -> C
    temps_24h[datetime.now().hour] = temp
    in_temp = round((request.args.get('indoortempf', type=float) - 32) / 1.8, 2)  # F -> C
    in_humi = request.args.get('indoorhumidity', type=int)  # %
    windchill = round((request.args.get('windchillf', type=float) - 32) / 1.8)  # F -> C
    humidity = request.args.get('humidity', type=int)  # %
    windspeed = round(round(request.args.get('windspeedmph', type=float) * 1.61))  # mph -> kmh
    windgust = round(round(request.args.get('windgustmph', type=float) * 1.61))  # mph -> kmh
    rain = round(request.args.get('rainin', type=float) * 25.4, 2)  # in -> cm
    dailyrain = round(request.args.get('dailyrainin', type=float) * 25.4, 2)  # in -> cm
    solarradiation = request.args.get('solarradiation', type=float)

    if c["debug"]:
        print(f"temp: {temp} C")
        print(f"intemp: {in_temp} C")
        print(f"windchill: {windchill} C")
        print(f"humidity: {humidity} %")
        print(f"windspeed: {windspeed} km/h")
        print(f"windgust: {windgust} km/h")
        print(f"rain: {rain} mm")
        print(f"dailyrain: {dailyrain} mm")
        print(f"solarradiation: {solarradiation} *")

    client.publish("jsons/weather/local/temps_24h", json.dumps(temps_24h))
    client.publish("home/weather/local/humidity", humidity)
    client.publish("home/weather/local/temperature", temp)
    client.publish("home/weather/local/windChill", windchill)
    client.publish("home/weather/local/windSpeed", windspeed)
    client.publish("home/weather/local/windGust", windgust)
    client.publish("home/weather/local/precipRate", rain)
    client.publish("home/weather/local/precipTotal", dailyrain)
    client.publish("home/weather/local/solarRadiation", solarradiation)
    client.publish("home/weather/sensors/temperature_upstairs_in", in_temp)
    client.publish("home/weather/sensors/humidity_upstairs_in", in_humi)

    return 'OK'


if __name__ == '__main__':
    client.loop_start()
    api.run(host="0.0.0.0", port=5005)
