from lxml import html
import requests

import asyncio
import time

from config import generalConfig as c
from common import HTTP_ALERT_AFTER, ConnectionLog, connect_mqtt, get_logger, setup_logging
from config import rehauConfig

log = get_logger("rehau")
rehau_log = ConnectionLog(log, "Rehau", alert_after=HTTP_ALERT_AFTER)
REHAU_TIMEOUT = 10  # seconds; local device, 60 s scrape cycle (change 020)

rooms = {
    0: "Hala",
    1: "Kupelna",
    2: "Technicka",
    3: "Pracovna",
    4: "Obyvacka-1",
    5: "Obyvacka-2",
    6: "Kuchyna",
}

async def main():
    client = connect_mqtt("rehau2")
    client.loop_start()
    print("[rehau] Started")

    while True:
        try:
            r = requests.get(url=rehauConfig["ip_address"] + "installer-room-page.html", timeout=REHAU_TIMEOUT)
            tree = html.fromstring(r.text)
            elements = tree.xpath('//div[@class="textCenter"]/form/button/div/text()')
            result_dict = {}
            for i in range(0, len(elements), 2):
                key = elements[i]
                value = elements[i + 1]
                result_dict[key] = value

            for room_id in [0, 1, 2, 3, 4, 6]:
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                r = requests.post(url=rehauConfig["ip_address"] + "room-operating.html", headers=headers, data=str(room_id)+"=",
                                  timeout=REHAU_TIMEOUT)
                tree = html.fromstring(r.text)
                room_name = tree.xpath('//button[@class="divRooms buttonRooms"]/input[@class="labelLeft pinkR fontArial roomName inputName"]')[0].value
                temp = tree.xpath('//button[@class="divRooms buttonRooms"]/label/text()')[0]
                temp_set = tree.xpath('//div[@class="textCenter"]/table/tr/td/input[@class="inputWPlHolder pinkR"]')[0].value
                humidity = tree.xpath('//span[@class="spanHum"]/label[@class="labelRight greyR fontArial"]/text()')[0].strip().rstrip('%')
                if c["debug"]: print(f"SET {room_name}: {temp_set}, {humidity}")
                client.publish("home/rehau/" + room_name, temp).wait_for_publish()
                client.publish("home/rehau_set/" + room_name, temp_set).wait_for_publish()
                client.publish("home/rehau_hum/" + room_name, int(humidity)).wait_for_publish()

            r = requests.get(url=rehauConfig["ip_address"] + "installer-inputoutput.html", timeout=REHAU_TIMEOUT)
            tree = html.fromstring(r.text)
            outputs = tree.xpath('//div[@class="textCenter"]/label/text()')[1].split(':')[1].strip()
            for i, room_val in enumerate(outputs.split(' ')[:7]):
                room_name = rooms[i]
                if c["debug"]: print(f"OUTPUT {room_name}: {room_val}")
                client.publish("home/rehau_output/" + room_name, room_val).wait_for_publish()
            rehau_log.ok()
        except Exception as e:
            rehau_log.failed(e, exc_info=True)
        time.sleep(60)


if __name__ == "__main__":
    setup_logging()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())