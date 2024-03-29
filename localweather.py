import json
from datetime import datetime

from flask import Flask, request

from config import generalConfig as c
from common import connect_mqtt, publishProperties

api = Flask(__name__)

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

    client.publish("jsons/weather/local/temps_24h", json.dumps(temps_24h), qos=2, properties=publishProperties)
    client.publish("home/weather/local/humidity", humidity, qos=2, properties=publishProperties)
    client.publish("home/weather/local/temperature", temp, qos=2, properties=publishProperties)
    client.publish("home/weather/local/windChill", windchill, qos=2, properties=publishProperties)
    client.publish("home/weather/local/windSpeed", windspeed, qos=2, properties=publishProperties)
    client.publish("home/weather/local/windGust", windgust, qos=2, properties=publishProperties)
    client.publish("home/weather/local/precipRate", rain, qos=2, properties=publishProperties)
    client.publish("home/weather/local/precipTotal", dailyrain, qos=2, properties=publishProperties)
    client.publish("home/weather/local/solarRadiation", solarradiation, qos=2, properties=publishProperties)
    client.publish("home/weather/sensors/temperature_upstairs_in", in_temp, qos=2, properties=publishProperties)
    client.publish("home/weather/sensors/humidity_upstairs_in", in_humi, qos=2, properties=publishProperties)

    return 'OK'


if __name__ == '__main__':
    client.loop_start()
    api.run(host="0.0.0.0", port=5005)
