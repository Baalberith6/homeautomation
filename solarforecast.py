import json
from datetime import datetime

import pytz as pytz
from dateutil.parser import parse

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from config import influxConfig
from secret import influxToken
from config import generalConfig as c

local_tz = pytz.timezone('Europe/Prague')


def _request():
    r = requests.get('https://api.forecast.solar/estimate/49.1503508/15.2338656/25/0/9.9')
    return r.json()


def store_runtime_data(r):
    client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    for key in r["result"]["watt_hours_period"].keys():
        day = local_tz.localize(parse(key))
        if day.date() == datetime.today().date():
            if c["debug"]:
                print(day, r["result"]["watt_hours_period"][key])
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("hourly", r["result"]["watt_hours_period"][key]).time(day))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("hourly_cummulative", r["result"]["watt_hours"][key]).time(day))

    for key in r["result"]["watt_hours_day"].keys():
        day = local_tz.localize(parse(key))
        if c["debug"]:
            print(parse(key), r["result"]["watt_hours_day"][key])
        write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("daily", r["result"]["watt_hours_day"][key]).time(day))
        break


def run():
    if (c["debug"]):
        store_runtime_data(json.loads('''
    {
        "result":
        {
            "watts":
            {
                "2023-01-10 07:49:00": 0,
                "2023-01-10 08:00:00": 71,
                "2023-01-10 09:00:00": 745,
                "2023-01-10 10:00:00": 1348,
                "2023-01-10 11:00:00": 1078,
                "2023-01-10 12:00:00": 917,
                "2023-01-10 13:00:00": 877,
                "2023-01-10 14:00:00": 707,
                "2023-01-10 15:00:00": 478,
                "2023-01-10 16:00:00": 95,
                "2023-01-10 16:23:00": 0,
                "2023-01-11 07:48:00": 0,
                "2023-01-11 08:00:00": 158,
                "2023-01-11 09:00:00": 437,
                "2023-01-11 10:00:00": 726,
                "2023-01-11 11:00:00": 862,
                "2023-01-11 12:00:00": 889,
                "2023-01-11 13:00:00": 841,
                "2023-01-11 14:00:00": 744,
                "2023-01-11 15:00:00": 457,
                "2023-01-11 16:00:00": 88,
                "2023-01-11 16:24:00": 0
            },
            "watt_hours_period":
            {
                "2023-01-10 07:49:00": 0,
                "2023-01-10 08:00:00": 7,
                "2023-01-10 09:00:00": 408,
                "2023-01-10 10:00:00": 1047,
                "2023-01-10 11:00:00": 1213,
                "2023-01-10 12:00:00": 998,
                "2023-01-10 13:00:00": 897,
                "2023-01-10 14:00:00": 792,
                "2023-01-10 15:00:00": 593,
                "2023-01-10 16:00:00": 287,
                "2023-01-10 16:23:00": 18,
                "2023-01-11 07:48:00": 0,
                "2023-01-11 08:00:00": 16,
                "2023-01-11 09:00:00": 298,
                "2023-01-11 10:00:00": 582,
                "2023-01-11 11:00:00": 794,
                "2023-01-11 12:00:00": 876,
                "2023-01-11 13:00:00": 865,
                "2023-01-11 14:00:00": 793,
                "2023-01-11 15:00:00": 601,
                "2023-01-11 16:00:00": 273,
                "2023-01-11 16:24:00": 18
            },
            "watt_hours":
            {
                "2023-01-10 07:49:00": 0,
                "2023-01-10 08:00:00": 7,
                "2023-01-10 09:00:00": 415,
                "2023-01-10 10:00:00": 1462,
                "2023-01-10 11:00:00": 2675,
                "2023-01-10 12:00:00": 3673,
                "2023-01-10 13:00:00": 4570,
                "2023-01-10 14:00:00": 5362,
                "2023-01-10 15:00:00": 5955,
                "2023-01-10 16:00:00": 6242,
                "2023-01-10 16:23:00": 6260,
                "2023-01-11 07:48:00": 0,
                "2023-01-11 08:00:00": 16,
                "2023-01-11 09:00:00": 314,
                "2023-01-11 10:00:00": 896,
                "2023-01-11 11:00:00": 1690,
                "2023-01-11 12:00:00": 2566,
                "2023-01-11 13:00:00": 3431,
                "2023-01-11 14:00:00": 4224,
                "2023-01-11 15:00:00": 4825,
                "2023-01-11 16:00:00": 5098,
                "2023-01-11 16:24:00": 5116
            },
            "watt_hours_day":
            {
                "2023-01-11": 5116,
                "2023-01-11": 5116
            }
        },
        "message":
        {
            "code": 0,
            "type": "success",
            "text": "",
            "info":
            {
                "latitude": 49.1504,
                "longitude": 15.2339,
                "distance": 0,
                "place": "37702:167, 40916, Malý Jeníkov, Strmilov, okres Jindřichův Hradec, Jihočeský kraj, Jihozápad, 378 53, Česko",
                "timezone": "Europe/Prague",
                "time": "2023-01-10T23:22:23+01:00",
                "time_utc": "2023-01-10T22:22:23+00:00"
            },
            "ratelimit":
            {
                "period": 3600,
                "limit": 12,
                "remaining": 8
            }
        }
    }
        '''))
    else:
        store_runtime_data(_request())


if __name__ == '__main__':
    run()
