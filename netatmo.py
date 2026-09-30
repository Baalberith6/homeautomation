import pyatmo
import logging

import asyncio
import time

from common import ConnectionLog, connect_mqtt, get_logger, setup_logging
from secret import netatmoClientId, netatmoClientSecret
from config import netatmoConfig
from config import generalConfig as c

# logging.basicConfig(filename='myapp.log', level=logging.DEBUG)
LOG = logging.getLogger(__name__)
log = get_logger("netatmo")
# A failed poll is a WARNING for the first 15 min, then an ERROR (change 020 revision 5).
NETATMO_GRACE_S = 15 * 60
api_log = ConnectionLog(log, "Netatmo", grace=NETATMO_GRACE_S)

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
    try:
        auth.refresh_tokens()
    except Exception as e:
        log.error(f"Netatmo login failed: {e}")
        raise
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

                client.publish("home/netatmo/temp_curr/"+room_name, room['therm_measured_temperature']).wait_for_publish()
                client.publish("home/netatmo/on/"+room_name, float(room['heating_power_request'])/100.0).wait_for_publish()
                if 'therm_setpoint_temperature' in room:
                    client.publish("home/netatmo/temp_target/"+room_name, room['therm_setpoint_temperature']).wait_for_publish()

                if c["debug"]: print(room['therm_measured_temperature'])
                if c["debug"]: print(room['heating_power_request'])
            api_log.ok()
        except Exception as e:
            api_log.failed(e, exc_info=True)
        time.sleep(60)
        # One poll a minute: the token is refreshed after 121 polls, before it expires after 3 h.
        # Before change 020 revision 5 nothing counted up, so this refresh never ran.
        tokenRefresher += 1


if __name__ == "__main__":
    setup_logging()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
