from paho.mqtt import client as mqtt_client
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from config import mqttConfig
from secret import mqttUsername, mqttPassword
from config import generalConfig as c

publishProperties=Properties(PacketTypes.PUBLISH)
publishProperties.MessageExpiryInterval = 86400  # in seconds


def connect_mqtt(client_id):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            if c["debug"]: print("Connected to MQTT Broker!")
        else:
            if c["debug"]: print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(mqttUsername, mqttPassword)
    client.on_connect = on_connect
    client.connect(mqttConfig["broker"], mqttConfig["port"])
    return client
