import json

import requests

from common import connect_mqtt, publishProperties
from config import azrouterConfig
from config import generalConfig as c
from paho.mqtt import client as mqtt_client


def _request(path: tuple):
    """Forward a raw request to Weather Underground APIs"""
    r = requests.get(azrouterConfig["ip_address"] + '/'.join(path))
    return r.json()


def process_inverter_message(msg, client):
    r = _request(("api", "v1", "power"))

    res = float(msg) - (r["input"]["power"][0]["value"] + r["input"]["power"][1]["value"] + r["input"]["power"][2]["value"])
    res = 0 if res < 200 else res

    client.publish("home/FVE/pretoky/bojlery", res, qos=2, properties=publishProperties)
    client.publish("home/FVE/pretoky/siet", r["input"]["power"][0]["value"] + r["input"]["power"][1]["value"] + r["input"]["power"][2]["value"], qos=2, properties=publishProperties)


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        process_inverter_message(json.loads(msg.payload), client)

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt("az")
    subscribe(client, ["home/FVE/meter_power"])
    client.loop_forever()


if __name__ == '__main__':
    run()
