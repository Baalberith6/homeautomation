import pyatmo
import logging
import traceback

import asyncio
import time

from common import connect_mqtt, publishProperties
from secret import netatmoClientId, netatmoClientSecret
from config import netatmoConfig
from config import generalConfig as c

# logging.basicConfig(filename='myapp.log', level=logging.DEBUG)
LOG = logging.getLogger(__name__)

def save_string_to_file(content):
    """
    Save a string into an existing file, overwriting the content.

    :param content: The string content to be written to the file.
    """
    try:
        with open(file_path, 'w') as file:
            file.write(content['refresh_token'])
            LOG.debug("WRITING '%s'", content['refresh_token'])
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
            LOG.debug("READ '%s'", content)
        return content
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None

file_path = 'netatmo.dev.token' if c["debug"] else 'netatmo.token'

async def main():
    client = connect_mqtt("netatmo4")
    client.loop_start()

    auth = pyatmo.NetatmoOAuth2(
        client_id=netatmoClientId,
        client_secret=netatmoClientSecret,
        scope="read_thermostat write_thermostat"
    )

    auth.extra["refresh_token"] = read_string_from_file()
    auth.token_updater = save_string_to_file
    auth.refresh_tokens()
    print("[netatmo] Started, token refreshed")
    tokenRefresher = 0

    home_status = pyatmo.HomeStatus(auth, home_id=netatmoConfig["home_id"])

    while True:
        try:
            if tokenRefresher > 120:
                auth.extra["refresh_token"] = read_string_from_file()
                auth.refresh_tokens()
                print("[netatmo] Token refreshed")
                tokenRefresher = 0

            home_status.update()
            for room_name in ["hala", "kupelna", "chodba", "hostovska", "julinka", "kubo", "spalna"]:
                room = home_status.rooms.get(netatmoConfig["room_id_" + room_name])

                client.publish("home/netatmo/temp_curr/"+room_name, room['therm_measured_temperature'], qos=2, properties=publishProperties).wait_for_publish()
                client.publish("home/netatmo/on/"+room_name, float(room['heating_power_request'])/100.0, qos=2, properties=publishProperties).wait_for_publish()

                if c["debug"]: print(room['therm_measured_temperature'])
                if c["debug"]: print(room['heating_power_request'])
        except Exception as e:
            print(f"[netatmo] Error: {e}")
            traceback.print_exc()
        time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
