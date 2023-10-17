import json
from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from paho.mqtt import client as mqtt_client

from common import connect_mqtt
from config import influxConfig
from secret import influxToken
from config import generalConfig as c

heat_lost = 0.143  # 0.143 kW/K

tc_base = 0.1  # 100W

# Toshiba 8kW COP 35C as the output temp until -7C
cop_45 = {
    -20: 1.5,
    -18: 1.6,
    -16: 1.7,
    -14: 1.8,
    -13: 1.9,
    -12: 2.0,
    -10: 2.1,
    -9: 2.2,
    -7: 3.2,
    -6: 3.3,
    -5: 3.4,
    -4: 3.5,
    -3: 3.5,
    -1: 3.6,
    0: 3.8,
    1: 4,
    2: 4, # 3.3kW
    3: 4,
    4: 4,
    5: 4,
    6: 4,
    7: 4.1, # 2.6kW
    8: 4.2,
    9: 4.3,
    10: 4.5,
    11: 5,
    12: 5, # 2.9kW
    13: 5,
    14: 5.2,
    100: 5.5
}

temperatures_inside = {
    0: 21,
    1: 21,
    2: 21,
    3: 21,
    4: 21,
    5: 21,
    6: 21,
    7: 21,
    8: 22,
    9: 22,
    10: 22,
    11: 22,
    12: 22,
    13: 22,
    14: 22,
    15: 22,
    16: 22,
    17: 22,
    18: 22,
    19: 22,
    20: 21,
    21: 21,
    22: 21,
    23: 21,
}

base_consumptions = {
    0: 0.250,
    1: 0.250,
    2: 0.250,
    3: 0.250,
    4: 0.250,
    5: 0.250,
    6: 0.250,
    7: 0.350,
    8: 0.500,
    9: 0.650,
    10: 0.800,
    11: 1.000,
    12: 0.500,
    13: 0.300,
    14: 0.500,
    15: 0.800,
    16: 0.800,
    17: 0.500,
    18: 0.300,
    19: 0.300,
    20: 0.300,
    21: 0.300,
    22: 0.300,
    23: 0.250,
}

tuv_consumptions = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
    8: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 4,
    13: 2,
    14: 0,
    15: 0,
    16: 0,
    17: 0,
    18: 0,
    19: 0,
    20: 0,
    21: 0,
    22: 0,
    23: 0,
}

influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        # if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        temps = json.loads(msg.payload.decode())
        total_tc_cummulative = 0
        total_primotop_cummulative = 0
        for temp, base_consumption, tuv_consumption, temp_in in zip(temps.items(), base_consumptions.values(), tuv_consumptions.values(), temperatures_inside.values()):
            cop = 100
            temp_in -= 5  # 5C diff base load + 4 ludia + pes
            total_tc = base_consumption + max(0, (((temp_in - temp[1]) * heat_lost) / cop)) + tc_base + (tuv_consumption / cop)
            total_primotop = base_consumption + max(0, ((temp_in - temp[1]) * heat_lost) + tuv_consumption)
            total_tc_cummulative += total_tc
            total_primotop_cummulative += total_primotop
            if c["debug"]: # -600s, because otherwise it was taken into next hour
                print(datetime.fromtimestamp(float(temp[0]) - 600.0), ": ", temp[1], "C : COP: ", cop, ": ")
                print("    base: ", base_consumption, "kW")
                print("    heat lost:", (14 - temp[1]) * heat_lost, "kW")
                print("    tc: ", total_tc, "kW/", total_tc_cummulative, "kW, primotop: ", total_primotop, "kW/", total_primotop_cummulative, "kW")
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("primotop", float(total_primotop)).time(datetime.fromtimestamp(float(temp[0]) - 600.0)))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("tc", float(total_tc)).time(datetime.fromtimestamp(float(temp[0]) - 600.0)))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("primotop_cummulative", float(total_primotop_cummulative)).time(datetime.fromtimestamp(float(temp[0]) - 600.0)))
            write_api.write(bucket=influxConfig["bucket"], record=Point("EnergyForecast").field("tc_cummulative", float(total_tc_cummulative)).time(datetime.fromtimestamp(float(temp[0]) - 600.0)))

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt("estimator")
    subscribe(client, ["jsons/weatherforecast/yr/tomorrow"])
    client.loop_forever()


if __name__ == '__main__':
    run()
