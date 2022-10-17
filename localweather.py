from flask import Flask, request

from config import generalConfig as c
from common import connect_mqtt

api = Flask(__name__)


@api.route('/weather', methods=['GET'])
def get_weather():
    temp = round((request.args.get('tempf', type=float) - 32) / 2)  # F -> C
    windchill = round((request.args.get('windchillf', type=float) - 32) / 2)  # F -> C
    humidity = request.args.get('humidity', type=int)  # %
    windspeed = round(round(request.args.get('windspeedmph', type=float) * 1.61))  # mph -> kmh
    windgust = round(round(request.args.get('windgustmph', type=float) * 1.61))  # mph -> kmh
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

    client = connect_mqtt("localweather")
    client.loop_start()

    client.publish("home/weather/local/humidity", humidity)
    client.publish("home/weather/local/temperature", temp)
    client.publish("home/weather/local/windChill", windchill)
    client.publish("home/weather/local/windSpeed", windspeed)
    client.publish("home/weather/local/windGust", windgust)
    client.publish("home/weather/local/precipRate", rain)
    client.publish("home/weather/local/precipTotal", dailyrain)
    client.publish("home/weather/local/solarRadiation", solarradiation)

    return 'OK'


if __name__ == '__main__':
    api.run(host="0.0.0.0", port=5005)
