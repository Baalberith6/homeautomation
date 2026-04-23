import time

import pyatmo
import requests

from paho.mqtt import client as mqtt_client

from config import rehauConfig, netatmoConfig, generalConfig as c
from secret import netatmoClientId, netatmoClientSecret

from common import connect_mqtt

termostat_temp_1np = 21.0
is_boosting = False

BOOST_OFFSET = 1.5

file_path = ('netatmo_optimizer.dev.token' if c["debug"]
             else 'netatmo_optimizer.token')

NETATMO_ROOMS = [
    "hala", "kupelna", "chodba", "hostovska",
    "julinka", "kubo", "spalna",
]

NETATMO_END_TIME_SECONDS = 7200  # 2 hours safety fallback


class Room:
    def __init__(self, id, name, currentTemp):
        self.id = id
        self.name = name
        self.currentTemp = currentTemp
    id: int
    name: str
    currentTemp: float


rooms = [
    Room(0, "Hala", 0),
    Room(1, "Kupelna", 0),
    Room(2, "Technicka", 0),
    Room(3, "Pracovna", 0),
    Room(4, "Obyvacka", 0),
    Room(5, "Obyvacka", 0),
    Room(6, "Kuchyna", 0),
]


def _request(payload: dict, path: str):
    r = requests.post(
        url=rehauConfig["ip_address"] + '/' + path, data=payload
    )
    return r


def save_string_to_file(content):
    try:
        with open(file_path, 'w') as file:
            file.write(content['refresh_token'])
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")


def read_string_from_file():
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
        return content
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None


def calc_rehau_temp(param):
    return 320 + 18 * param


def apply_thermostats(include_netatmo=True):
    temp = (termostat_temp_1np + BOOST_OFFSET
            if is_boosting else termostat_temp_1np)

    if c["debug"]:
        print(f"[estia_optimizer] apply_thermostats: "
              f"boosting={is_boosting}, temp={temp}, "
              f"rehau={include_netatmo}")

    # Rehau zones
    for room in rooms:
        payload = {
            'zone': room.id,
            'RoomName': room.name,
            'RSH': temp,
            'lightH': '0',
            'temp': calc_rehau_temp(temp),
            'mode': 'normal'
        }
        if room.currentTemp != temp:
            try:
                _request(payload, "room-page.html")
                room.currentTemp = temp
            except Exception as e:
                print(f"[estia_optimizer] Rehau {room.name} error: {e}")
        elif c["debug"]:
            print(f"[estia_optimizer] Rehau {room.name} already at {temp}")

    # Netatmo rooms (only on boost transitions, not on base temp changes)
    if include_netatmo:
        try:
            timestamp = int(time.time())
            end_time = timestamp + NETATMO_END_TIME_SECONDS

            auth = pyatmo.NetatmoOAuth2(
                client_id=netatmoClientId,
                client_secret=netatmoClientSecret,
                scope="read_thermostat write_thermostat"
            )
            auth.extra["refresh_token"] = read_string_from_file()
            auth.token_updater = save_string_to_file
            auth.refresh_tokens()

            home_status = pyatmo.HomeStatus(
                auth, home_id=netatmoConfig["home_id"]
            )
            for room_name in NETATMO_ROOMS:
                room_id = netatmoConfig["room_id_" + room_name]
                if c["debug"]:
                    print(f"[estia_optimizer] Netatmo {room_name}: "
                          f"manual {temp}C, "
                          f"end_time +{NETATMO_END_TIME_SECONDS}s")
                home_status.set_room_thermpoint(
                    mode="manual", temp=temp,
                    room_id=room_id, end_time=end_time
                )
        except Exception as e:
            print(f"[estia_optimizer] Netatmo error: {e}")

    print(f"[estia_optimizer] Thermostats set to {temp}C "
          f"(boosting={is_boosting})")


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        topicParts = msg.topic.split("/")
        if len(topicParts) < 2:
            return

        if topicParts[1] == "estia":  # heating compressor state
            global is_boosting
            active = msg.payload.decode() == "True"
            if c["debug"]:
                print(f"[estia_optimizer] heating_compressor_active="
                      f"{active}, is_boosting={is_boosting}")
            if active and not is_boosting:
                print("[estia_optimizer] Starting boost: "
                      "heating compressor active")
                is_boosting = True
                apply_thermostats()
            elif not active and is_boosting:
                print("[estia_optimizer] Stopping boost: "
                      "heating compressor inactive")
                is_boosting = False
                apply_thermostats()
        elif topicParts[1] == "rehau_set":
            if c["debug"]:
                print(f"Received `{msg.payload.decode()}` "
                      f"from `{msg.topic}` topic")
            for room in rooms:
                if room.name == topicParts[2]:
                    room.currentTemp = float(msg.payload.decode())
        elif topicParts[1] == "Termostat1NP":
            global termostat_temp_1np
            new_temp = float(msg.payload.decode())
            if new_temp != termostat_temp_1np:
                print(f"[estia_optimizer] Termostat1NP changed: "
                      f"{termostat_temp_1np} -> {new_temp}")
                termostat_temp_1np = new_temp
                apply_thermostats(include_netatmo=False)
            elif c["debug"]:
                print(f"Received `{msg.payload.decode()}` "
                      f"from `{msg.topic}` topic")

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message


def init():
    client = connect_mqtt("estia_optimizer")
    subscribe(client, [
        "bool/estia/heating_compressor_active",
        "home/rehau_set/#",
        "command/Termostat1NP",
    ])
    print("[estia_optimizer] Started")
    client.loop_forever()


if __name__ == '__main__':
    init()
