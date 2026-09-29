import asyncio
import time

import requests

from config import generalConfig as c, grafanaConfig
from secret import grafanaApiKey
from common import ConnectionLog, connect_mqtt, get_logger, setup_logging

log = get_logger("grafana_setter")
api_log = ConnectionLog(log, "Grafana API")


def _request():
    headers = {"Authorization": f"Bearer {grafanaApiKey}"}
    # 4 s: shorter than the 5 s poll (change 020).
    r = requests.get(grafanaConfig["ip_address"] + 'api/dashboards/uid/' + grafanaConfig["dashboard_id"],
                     headers=headers, timeout=4)
    return r.json()


def fetch_variables():
    """The template variables of the dashboard, or None after a failed fetch (change 020).

    After a failure the service publishes nothing in that cycle, so no old or partial setpoint goes out.
    """
    try:
        data = _request()["dashboard"]["templating"]["list"]
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        api_log.failed(e)
        return None
    api_log.ok()
    return data


async def publish(client):
    while True:
        data = fetch_variables()
        if data is not None:
            for item in data:
                client.publish("command/"+item["name"], item["current"]["value"])
                if (c["debug"]):
                    print(f"{item['name']}: {item['current']['value']}")

        time.sleep(5)


def run():
    client = connect_mqtt("grafana_set")
    client.loop_start()
    asyncio.run(publish(client))


if __name__ == '__main__':
    setup_logging()
    run()
