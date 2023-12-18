import pyatmo

import asyncio
import time

from common import connect_mqtt, publishProperties
from secret import netatmoClientId, netatmoClientSecret, netatmoRefreshToken
from config import netatmoConfig
from config import generalConfig as c

async def main():
    client = connect_mqtt("netatmo")
    client.loop_start()

    auth = pyatmo.NetatmoOAuth2(
        client_id=netatmoClientId,
        client_secret=netatmoClientSecret,
        scope="read_thermostat"
    )

    auth.extra["refresh_token"] = netatmoRefreshToken
    auth.refresh_tokens()
    tokenRefresher = 0

    home_status = pyatmo.HomeStatus(auth, home_id=netatmoConfig["home_id"])

    while True:
        if tokenRefresher > 120:
            auth.refresh_tokens()
            tokenRefresher = 0

        home_status.update()
        room = home_status.rooms.get(netatmoConfig["room_id"])
        thermostat = home_status.thermostats.get(netatmoConfig["thermostat_id"])

        client.publish("home/netatmo/temp_curr", room['therm_measured_temperature'], qos=2, properties=publishProperties).wait_for_publish()
        client.publish("bool/netatmo/on", thermostat["boiler_status"], qos=2, properties=publishProperties).wait_for_publish()

        if c["debug"]: print(room['therm_measured_temperature'])
        if c["debug"]: print(thermostat["boiler_status"])
        time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
