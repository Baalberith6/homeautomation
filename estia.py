import asyncio

from estia_api import ToshibaAcHttpApi

import time

from common import connect_mqtt, publishProperties
from secret import toshibaUsername, toshibaSecret
from config import generalConfig as c, estiaConfig

def hex_to_number(hex_code):
    num = int(hex_code, 16)
    return (num - 72) / 2 + 20

def hex_to_guess_number(hex_code):
    num = int(hex_code, 16)
    return (num - 56) / 2 + 4

async def main():
    client = connect_mqtt("toshiba-estia")
    client.loop_start()

    api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret)
    await api.connect()
    await api.get_devices()
    while True:
        sensors = await api.get_device_detail(estiaConfig["device_unique_id"])
        if (c["debug"]): print(sensors)
        s = sensors["ACStateData"]
        data = {
            "waterActive": s[:2] == "0c",
            "waterTemp": hex_to_number(s[2:4]),
            "waterActiveCompressor": s[4:6] == "01",
            "waterActiveCoil": s[6:8] == "01",
            "heatingActive": s[8:10] == "03",
            "1112": s[10:12],
            "manualHeatingTemp": hex_to_number(s[12:14]),
            "autoHeatingTemp": hex_to_number(s[14:16]),
            "heatingActiveCompressor": s[16:18] == "01",
            "heatingActiveCoil": s[18:20] == "01",
            "2122": s[20:22],
            "2324": s[22:24],
            "2526": s[24:26],
            "heatingTempMin": hex_to_number(s[26:28]),
            "2930": hex_to_number(s[28:30]),
            "3132": s[30:32],
            "3334": s[32:34],
        }
        if (c["debug"]): print(data)
        in_temp = hex_to_guess_number(sensors["TWI_Temp"])
        out_temp = hex_to_guess_number(sensors["TWO_Temp"])
        target_temp = data["autoHeatingTemp"]
        compressor_active = data["waterActiveCompressor"] or data["heatingActiveCompressor"]

        client.publish("home/estia/in_temp", in_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/estia/out_temp", out_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/estia/target_temp", target_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("bool/estia/compressor_active", compressor_active, qos=2, properties=publishProperties).wait_for_publish()

        time.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
