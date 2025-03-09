import asyncio
import time

import requests

from config import generalConfig as c, grafanaConfig
from secret import grafanaApiKey
from common import connect_mqtt, publishProperties

def _request():
    headers = {"Authorization": f"Bearer {grafanaApiKey}"}
    r = requests.get(grafanaConfig["ip_address"] + 'api/dashboards/uid/' + grafanaConfig["dashboard_id"], headers=headers)
    return r.json()

async def publish(client):
    while True:
        data = _request()["dashboard"]["templating"]["list"]
        for item in data:
            client.publish("command/"+item["name"], item["current"]["value"], qos=2, properties=publishProperties)
            if (c["debug"]):
                print(f"{item['name']}: {item['current']['value']}")

        time.sleep(5)


def run():
    client = connect_mqtt("grafana_set")
    client.loop_start()
    asyncio.run(publish(client))


if __name__ == '__main__':
    run()
