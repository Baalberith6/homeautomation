import json
import time
from datetime import datetime

import pyatmo
import requests

from paho.mqtt import client as mqtt_client

from config import rehauConfig, netatmoConfig, generalConfig as c
from secret import netatmoClientId, netatmoClientSecret

from common import connect_mqtt

last_water_temp = 100.0
last_last_water_temp = 100.0
target_temp = 27.0
outside_temp = 0.0
outside_temp_limit = -3.0 # when to stop optimizing

hysteresis_above = 1.0 # krb protection

file_path = 'netatmo_optimizer.token'

class Room:
    def __init__(self, id, name, normalTemp, currentTemp):
        self.id = id
        self.name = name
        self.normalTemp = normalTemp
        self.currentTemp = currentTemp
    id: int
    name: str
    normalTemp: float
    currentTemp: float

rooms = [
    Room(0, "Hala", rehauConfig["temp_hala"], 0),
    Room(1, "Kupelna", rehauConfig["temp_all"], 0),
    Room(2, "Technicka", rehauConfig["temp_all"], 0),
    Room(3, "Pracovna", rehauConfig["temp_all"], 0),
    Room(4, "Obyvacka", rehauConfig["temp_all"], 0),
    Room(5, "Obyvacka", rehauConfig["temp_all"], 0),
    Room(6, "Kuchyna", rehauConfig["temp_all"], 0),
]

def _request(payload:dict, path: str):
    r = requests.post(url=rehauConfig["ip_address"] + '/' + path, data=payload)
    return r


def save_string_to_file(content):
    """
    Save a string into an existing file, overwriting the content.

    :param content: The string content to be written to the file.
    """
    try:
        with open(file_path, 'w') as file:
            file.write(content['refresh_token'])
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")

def read_string_from_file():
    """
    Read the string content from a file.

    :return: The string content read from the file.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
        return content
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None


def calc_rehau_temp(param):
    return 320 + 18 * param

def rehau_set(op:str):
    global outside_temp
    tempAdjustment = 1.0 if outside_temp < 4.5 else 0.5
    for room in rooms:
        temp = room.normalTemp if op == "stop" else room.normalTemp + tempAdjustment
        payload = {
            'zone': room.id,
            'RoomName': room.name,
            'RSH': temp,
            'lightH': '0',
            'temp': calc_rehau_temp(temp),
            'mode': 'normal'
        }
        if room.currentTemp != temp and outside_temp > outside_temp_limit:
            if c["debug"]: print(f"Starting Rehau because we are just about to start heating")
            _request(payload, "room-page.html")
        else:
            if c["debug"]: print(f"No operation Rehau because either <1C outside, real ({outside_temp})C or temp already set ({temp})")
    return

def netatmo_set(op:str, add_time:int):
    timestamp = int("{:.0f}".format(time.time()))
    auth = pyatmo.NetatmoOAuth2(
        client_id=netatmoClientId,
        client_secret=netatmoClientSecret,
        scope="read_thermostat write_thermostat"
    )

    auth.extra["refresh_token"] = read_string_from_file()
    auth.token_updater = save_string_to_file
    auth.refresh_tokens()

    home_status = pyatmo.HomeStatus(auth, home_id=netatmoConfig["home_id"])
    home_status.update()
    room = home_status.rooms.get(netatmoConfig["room_id"])
    if op == "start":
        temp = room.get("therm_setpoint_temperature") if room.get("therm_setpoint_mode") == "manual" else room.get("therm_setpoint_temperature") + 1 # 1C above planned temp
        end_time = max(timestamp+add_time, room.get("therm_setpoint_end_time", 0))
        if outside_temp > outside_temp_limit:
            if c["debug"]: print(f"Setting manual temp: {temp} with time: {end_time-timestamp}s")
            home_status.set_room_thermpoint(mode="manual", temp=temp, room_id=netatmoConfig["room_id"], end_time=end_time)
        else:
            if c["debug"]: print(f"Netatmo Outside temp < -3C, skipping..")
    elif op == "stop":
        if c["debug"]: print(f"Netatmo stop")
        home_status.set_room_thermpoint(mode="home", room_id=netatmoConfig["room_id"])


def decide(last_last_water_temp, last_water_temp, new_water_temp, target_temp):
    if c["debug"]: print(f"At {datetime.now()}, deciding based on 'new water': {new_water_temp}C, 'last water': {last_water_temp}C, 'last-last water': {last_last_water_temp}C, 'target': {target_temp}C")

    trend_up = new_water_temp > last_water_temp > last_last_water_temp
    if trend_up and (new_water_temp < (target_temp + hysteresis_above)):  # while heating up - TC running
        rehau_set("start")
        if new_water_temp < (target_temp + 0.5):
            netatmo_set(op="start", add_time=1800)
        else:
            netatmo_set(op="start", add_time=900)
        return

    trend_down = new_water_temp < last_water_temp < last_last_water_temp
    if trend_down:
        if c["debug"]: print(f"Stopping Rehau because heating stopped")
        rehau_set("stop")
        return

    if c["debug"]: print(f"Doing nothing..")

def loop(new_water_temp):
    global last_water_temp
    global last_last_water_temp
    global target_temp

    decide(last_last_water_temp, last_water_temp, new_water_temp, target_temp)

    last_last_water_temp = last_water_temp
    last_water_temp = new_water_temp

def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        topicParts = msg.topic.split("/")
        if len(topicParts) < 2:
            return

        if topicParts[0] == "krb": # current water temp
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global target_temp
            res = json.loads(msg.payload.decode())
            loop(float(res["tC"]))
        elif topicParts[1] == "estia": # target estia temp
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global target_temp
            target_temp = float(msg.payload.decode())
        elif topicParts[1] == "weather":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global outside_temp
            outside_temp = float(msg.payload.decode())
        elif topicParts[1] == "rehau_set":
            if c["debug"]: print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            global rooms
            for room in rooms:
                if room.name == topicParts[2]:
                    room.currentTemp = float(msg.payload.decode())

    for topic in topics:
        client.subscribe(topic)
    client.on_message = on_message

def init():
    client = connect_mqtt("estia_optimizer")
    subscribe(client, ["home/estia/target_temp", "krb/status/temperature:101", "home/weather/local/temperature", "home/rehau_set/#"])
    client.loop_forever()


if __name__ == '__main__':
    init()

