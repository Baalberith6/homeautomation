import json
from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from paho.mqtt import client as mqtt_client

from common import connect_mqtt
from config import influxConfig
from secret import influxToken
from config import generalConfig as c

heat_lost = 125  # 125 W/K

tc_base = 50

# nibe COP
cop_35 = {
    -20: 2.4,
    -18: 2.5,
    -16: 2.6,
    -14: 2.7,
    -13: 2.8,
    -12: 2.9,
    -11: 3.0,
    -10: 3.1,
    -9: 3.2,
    -7: 3.3,
    -6: 3.4,
    -5: 3.5,
    -4: 3.6,
    -3: 3.7,
    -1: 3.8,
    0: 3.9,
    1: 4.0,
    2: 4.1,
    3: 4.2,
    4: 4.3,
    5: 4.4,
    6: 4.5,
    7: 4.7,
    8: 4.8,
    9: 5.0,
    10: 5.1,
    11: 5.3,
    12: 5.4,
    13: 5.5,
    14: 5.7,
    100: 5.8
}

base_consumptions = {
    0: 250,
    1: 250,
    2: 250,
    3: 250,
    4: 250,
    5: 250,
    6: 250,
    7: 350,
    8: 500,
    9: 550,
    10: 500,
    11: 500,
    12: 300,
    13: 300,
    14: 300,
    15: 500,
    16: 500,
    17: 500,
    18: 300,
    19: 300,
    20: 300,
    21: 300,
    22: 300,
    23: 250,
}

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        # if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        temps = json.loads(msg.payload.decode())
        total_tc_cummulative = 0
        total_primotop_cummulative = 0
        for temp, base_consumption in zip(temps.items(), base_consumptions.values()):
            cop = 100
            for cop_curr in cop_35.items():
                if cop_curr[0] > float(temp[1]):
                    cop = cop_curr[1]
                    break
            total_tc = max(0, base_consumption + (((14 - temp[1]) * heat_lost) / cop) + tc_base)
            total_primotop = max(0, base_consumption + ((14 - temp[1]) * heat_lost))
            total_tc_cummulative += total_tc
            total_primotop_cummulative += total_primotop
            if c["debug"]:
                print(datetime.fromtimestamp(float(temp[0])), ": ", temp[1], "C : ", cop, ": ", base_consumption, "W : ", (14 - temp[1]) * heat_lost, "W: ", total_tc, "W: ", total_primotop, "W")
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("primotop", float(total_primotop)).time(datetime.fromtimestamp(float(temp[0]))))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("tc", float(total_tc)).time(datetime.fromtimestamp(float(temp[0]))))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("primotop_cummulative", float(total_primotop_cummulative)).time(datetime.fromtimestamp(float(temp[0]))))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("tc_cummulative", float(total_tc_cummulative)).time(datetime.fromtimestamp(float(temp[0]))))

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt("estimator")
    subscribe(client, ["jsons/weatherforecast/yr/tomorrow"])
    client.loop_forever()


if __name__ == '__main__':
    run()