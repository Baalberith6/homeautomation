import asyncio
from math import dist

from estia_api import ToshibaAcHttpApi

import time

from common import connect_mqtt, publishProperties
from secret import toshibaUsername, toshibaSecret
from config import generalConfig as c, estiaConfig

def hex_to_number(hex_code):
    num = int(hex_code, 16)
    return num - 32

def hex_to_number_2(hex_code):
    num = int(hex_code, 16)
    return num - 48 + (0 if num < 100 else 2) # no idea why
# a4 -> 60
# a6 -> 62
# a7 -> 63 // 62,5?
# 86 -> 43
# 74 -> 34
# 6c -> 29.5
# 64 -> 26

async def main():
    client = connect_mqtt("toshiba-estia")
    client.loop_start()

    api = ToshibaAcHttpApi(toshibaUsername, toshibaSecret)
    await api.connect()
    await api.get_devices()
    previous_in_temp = 0
    previous_out_temp = 0
    tuv_active_latest = 999
    while True:
        sensors = await api.get_device_detail(estiaConfig["device_unique_id"])
        if (c["debug"]): print(sensors)
        s = sensors["ACStateData"]
        tuv_compressor_active = s[4:6] == "01"
        tuv_coil_active = s[6:8] == "01"
        tuv_active = tuv_compressor_active or tuv_coil_active
        tuv_active_latest = 0 if tuv_active else tuv_active_latest + 1
        data = {
            "waterActive": s[:2] == "0c",
            "waterTemp": hex_to_number(s[2:4]),
            "waterActiveCompressor": tuv_compressor_active,
            "waterActiveCoil": tuv_coil_active,
            "heatingActive": s[8:10] == "03", # maybe pump?
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
        if not tuv_compressor_active and not tuv_coil_active and tuv_active_latest > 10: # TUV not active for 10 minutes
            in_temp = hex_to_number_2(sensors["TWI_Temp"])
            out_temp = hex_to_number_2(sensors["TWO_Temp"])
        else:
            in_temp = previous_in_temp
            out_temp = previous_out_temp
        target_temp = data["autoHeatingTemp"]
        compressor_active = data["waterActiveCompressor"] or data["heatingActiveCompressor"]

        client.publish("home/estia/in_temp", in_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/estia/out_temp", out_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("home/estia/target_temp", target_temp, qos=2, properties=publishProperties).wait_for_publish()
        client.publish("bool/estia/compressor_active", compressor_active, qos=2, properties=publishProperties).wait_for_publish()

        previous_in_temp = in_temp
        previous_out_temp = out_temp
        time.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
