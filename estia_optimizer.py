import time
from datetime import datetime

import pyatmo
import requests

from paho.mqtt import client as mqtt_client

from config import rehauConfig, netatmoConfig, generalConfig as c
from secret import netatmoClientId, netatmoClientSecret

from common import ConnectionLog, connect_mqtt, get_logger, setup_logging, subscribe_on_connect

log = get_logger("estia_optimizer")
rehau_log = ConnectionLog(log, "Rehau")

termostat_temp_1np = None  # None until the first command/Termostat1NP (change 024, D10)
TERMOSTAT_DEFAULT = 21.0   # used by a boost that comes before the first command/Termostat1NP
is_boosting = False
applied_is_day = None      # the window of the last Rehau write

BOOST_OFFSET = 1.0         # both floors, while the heating compressor runs (024, D5)
NIGHT_OFFSET = -1.0        # ground floor only, outside the day window (024, D2)
DAY_START_HOUR = 7         # the day window is 07:00-18:59 local time (024, D7)
DAY_END_HOUR = 19

file_path = ('netatmo_optimizer.dev.token' if c["debug"]
             else 'netatmo_optimizer.token')

NETATMO_ROOMS = [
    "hala", "kupelna", "chodba", "hostovska",
    "julinka", "kubo", "spalna",
]

NETATMO_END_TIME_SECONDS = 14400  # 4 hours safety fallback


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
        url=rehauConfig["ip_address"] + '/' + path, data=payload,
        timeout=10,  # seconds; the local Rehau controller (change 020)
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


def _now():
    return datetime.now()


def is_day(hour):
    return DAY_START_HOUR <= hour < DAY_END_HOUR


def setpoints(termostat, day, boosting):
    """Returns (rehau, netatmo). Rehau drops at night; both get the boost (change 024)."""
    boost = BOOST_OFFSET if boosting else 0
    rehau = termostat + (0 if day else NIGHT_OFFSET) + boost
    return rehau, termostat + boost


def _log_window(old_day, new_day):
    termostat = (termostat_temp_1np if termostat_temp_1np is not None
                 else TERMOSTAT_DEFAULT)
    base = termostat + (0 if new_day else NIGHT_OFFSET)
    names = {True: "day", False: "night"}
    log.info(f"Window {names[old_day]} -> {names[new_day]}: "
             f"Rehau base {base}C")


def apply_thermostats(include_netatmo=True):
    termostat = (termostat_temp_1np if termostat_temp_1np is not None
                 else TERMOSTAT_DEFAULT)
    temp, netatmo_temp = setpoints(termostat, is_day(_now().hour),
                                   is_boosting)

    if c["debug"]:
        print(f"[estia_optimizer] apply_thermostats: "
              f"boosting={is_boosting}, rehau={temp}, "
              f"netatmo={netatmo_temp}, include_netatmo={include_netatmo}")

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
                r = _request(payload, "room-page.html")
                # Change 020: a failed POST is logged; the control rule stays as it was.
                if 200 <= r.status_code < 300:
                    rehau_log.ok()
                else:
                    rehau_log.failed(f"{room.name}: HTTP {r.status_code}")
                room.currentTemp = temp
            except Exception as e:
                rehau_log.failed(f"{room.name}: {e}")
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
                          f"manual {netatmo_temp}C, "
                          f"end_time +{NETATMO_END_TIME_SECONDS}s")
                home_status.set_room_thermpoint(
                    mode="manual", temp=netatmo_temp,
                    room_id=room_id, end_time=end_time
                )
        except Exception as e:
            log.error(f"Netatmo error: {e}")

    netatmo_note = "" if include_netatmo else " (Netatmo not written)"
    print(f"[estia_optimizer] Thermostats set: Rehau {temp}C, "
          f"Netatmo {netatmo_temp}C{netatmo_note} "
          f"(boosting={is_boosting})")


def subscribe(client: mqtt_client, topics: [str]):
    def on_message(client, userdata, msg):
        topicParts = msg.topic.split("/")
        if len(topicParts) < 2:
            return

        global applied_is_day, is_boosting, termostat_temp_1np
        if topicParts[1] == "estia":  # heating compressor state
            active = msg.payload.decode() == "True"
            day = is_day(_now().hour)
            if c["debug"]:
                print(f"[estia_optimizer] heating_compressor_active="
                      f"{active}, is_boosting={is_boosting}")
            if active and not is_boosting:
                print("[estia_optimizer] Starting boost: "
                      "heating compressor active")
                is_boosting = True
                applied_is_day = day
                apply_thermostats()
            elif not active and is_boosting:
                print("[estia_optimizer] Stopping boost: "
                      "heating compressor inactive")
                is_boosting = False
                applied_is_day = day
                apply_thermostats()
            elif (termostat_temp_1np is not None
                  and applied_is_day is not None
                  and day != applied_is_day):  # change 024, rules 1 and 2
                _log_window(applied_is_day, day)
                applied_is_day = day
                apply_thermostats(include_netatmo=False)
        elif topicParts[1] == "rehau_set":
            if c["debug"]:
                print(f"Received `{msg.payload.decode()}` "
                      f"from `{msg.topic}` topic")
            for room in rooms:
                if room.name == topicParts[2]:
                    room.currentTemp = float(msg.payload.decode())
        elif topicParts[1] == "Termostat1NP":
            new_temp = float(msg.payload.decode())
            day = is_day(_now().hour)
            first = termostat_temp_1np is None  # change 024, rule 3
            window_changed = (applied_is_day is not None
                              and day != applied_is_day)  # rule 1
            if first or new_temp != termostat_temp_1np or window_changed:
                if new_temp != termostat_temp_1np:
                    print(f"[estia_optimizer] Termostat1NP changed: "
                          f"{termostat_temp_1np} -> {new_temp}")
                termostat_temp_1np = new_temp
                if window_changed:
                    _log_window(applied_is_day, day)
                applied_is_day = day
                apply_thermostats(include_netatmo=False)
            else:
                applied_is_day = day
                if c["debug"]:
                    print(f"Received `{msg.payload.decode()}` "
                          f"from `{msg.topic}` topic")

    subscribe_on_connect(client, topics)
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
    setup_logging()
    init()
