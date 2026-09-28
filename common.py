from paho.mqtt import client as mqtt_client
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from config import mqttConfig
from secret import mqttUsername, mqttPassword
from config import generalConfig as c

publishProperties=Properties(PacketTypes.PUBLISH)
publishProperties.MessageExpiryInterval = 86400  # in seconds


class DefaultPublishClient(mqtt_client.Client):
    """paho Client whose publish() uses QoS 2 and publishProperties by default (change 013, D7)."""

    def publish(self, topic, payload=None, qos=2, retain=False, properties=publishProperties):
        return super().publish(topic, payload, qos, retain, properties)


def connect_mqtt(client_id):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            if c["debug"]: print("Connected to MQTT Broker!")
        else:
            if c["debug"]: print("Failed to connect, return code %d\n", reason_code)

    if c["debug"]:
        client_id = client_id + "-dev"
    client = DefaultPublishClient(client_id=client_id, protocol=mqtt_client.MQTTv5)
    client.username_pw_set(mqttUsername, mqttPassword)
    client.on_connect = on_connect
    client.connect(mqttConfig["broker"], mqttConfig["port"])
    return client
