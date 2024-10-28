from lxml import html
import requests

import asyncio
import time

from config import generalConfig as c
from common import connect_mqtt, publishProperties
from config import rehauConfig

async def main():
    client = connect_mqtt("rehau")
    client.loop_start()

    while True:
        r = requests.get(url=rehauConfig["ip_address"] + "installer-room-page.html")
        tree = html.fromstring(r.text)
        elements = tree.xpath('//div[@class="textCenter"]/form/button/div/text()')
        result_dict = {}
        for i in range(0, len(elements), 2):
            key = elements[i]
            value = elements[i + 1]
            result_dict[key] = value

        for(key, value) in result_dict.items():
            if c["debug"]: print(f"{key}: {value}")
            client.publish("home/rehau/" + key, value, qos=2,  properties=publishProperties).wait_for_publish()

        for room_id in [0, 1, 2, 3, 4, 6]:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            r = requests.post(url=rehauConfig["ip_address"] + "room-operating.html",headers=headers, data=str(room_id)+"=")
            tree = html.fromstring(r.text)
            room_name = tree.xpath('//button[@class="divRooms buttonRooms"]/input[@class="labelLeft pinkR fontArial roomName inputName"]')[0].value
            temp = tree.xpath('//div[@class="textCenter"]/table/tr/td/input[@class="inputWPlHolder pinkR"]')[0].value
            if c["debug"]: print(f"SET {room_name}: {temp}")
            client.publish("home/rehau_set/" + room_name, temp, qos=2,  properties=publishProperties).wait_for_publish()
        time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())