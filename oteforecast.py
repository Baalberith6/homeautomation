import json
from datetime import timedelta, datetime
from pprint import pprint

import pytz as pytz

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from common import connect_mqtt, publishProperties
from config import generalConfig as c, influxConfig
from secret import influxToken

local_tz = pytz.timezone('Europe/Prague')


def _request(date: datetime):
    r = requests.get('https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data?report_date=' + date.strftime("%Y-%m-%d"))
    return r.json()


def send_to_mqtt(r, client, date: datetime):
    influx_client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)

    data = r["data"]["dataLine"]
    hour_prices = data[next(index for index, element in enumerate(data)
                            if element["title"].__contains__("EUR"))]["point"]
    if (c["debug"]):
        pprint(hour_prices)
    hour_prices_dict = {}

    for hour in hour_prices:
        hour_prices_dict[hour["x"]] = hour["y"]

    client.publish("home/OTE/hourly", json.dumps(hour_prices_dict), qos=2, properties=publishProperties).wait_for_publish()
    hour_prices_zal = hour_prices_dict.copy()

    max_hour = max(hour_prices_dict, key=hour_prices_dict.get)
    hour_prices_dict.pop(max_hour)
    max_hour2 = max(hour_prices_dict, key=hour_prices_dict.get)
    hour_prices_dict.pop(max_hour2)
    max_hour3 = max(hour_prices_dict, key=hour_prices_dict.get)

    min_hour = min(hour_prices_dict, key=hour_prices_dict.get)
    hour_prices_dict.pop(min_hour)
    min_hour2 = min(hour_prices_dict, key=hour_prices_dict.get)
    hour_prices_dict.pop(min_hour2)
    min_hour3 = min(hour_prices_dict, key=hour_prices_dict.get)
    if (c["debug"]): print(max_hour, max_hour2, max_hour3, min_hour, min_hour2, min_hour3)

    max_hours_out = {max_hour: hour_prices_zal[max_hour], max_hour2: hour_prices_zal[max_hour2], max_hour3: hour_prices_zal[max_hour3]}
    min_hours_out = {min_hour: hour_prices_zal[min_hour], min_hour2: hour_prices_zal[min_hour2], min_hour3: hour_prices_zal[min_hour3]}
    client.publish("home/OTE/daily/max/hour", max_hour, qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/OTE/daily/max/price", hour_prices_zal[max_hour], qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/OTE/daily/min/hour", min_hour, qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/OTE/daily/min/price", hour_prices_zal[min_hour], qos=2, properties=publishProperties).wait_for_publish()

    print(date + timedelta(hours=int(max_hour)))
    write_api.write(bucket=influxConfig["bucket"], record=Point("OTE").field("price", hour_prices_zal[max_hour]).tag("type", "max").time(date + timedelta(hours=int(max_hour))))
    write_api.write(bucket=influxConfig["bucket"], record=Point("OTE").field("price", hour_prices_zal[min_hour]).tag("type", "min").time(date + timedelta(hours=int(min_hour))))

    # hour_prices
    # for key in r["result"]["watt_hours_period"].keys():
    #     day = local_tz.localize(parse(key))
    #     if day.date() == datetime.today().date():
    #         if c["debug"]:
    #             print(day, r["result"]["watt_hours_period"][key])
    #         write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("hourly", r["result"]["watt_hours_period"][key]).time(day))
    #         write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("hourly_cummulative", r["result"]["watt_hours"][key]).time(day))
    #
    # for key in r["result"]["watt_hours_day"].keys():
    #     day = local_tz.localize(parse(key))
    #     if c["debug"]:
    #         print(parse(key), r["result"]["watt_hours_day"][key])
    #     write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("daily", r["result"]["watt_hours_day"][key]).time(day))
    #     break


def run():
    client = connect_mqtt("ote")
    client.loop_start()
    if (not c["debug"]):
        send_to_mqtt(json.loads('''
{
    "axis": {
        "x": {
            "decimals": 0,
            "legend": "Hodina",
            "short": false,
            "step": 1
        },
        "y": {
            "decimals": 0,
            "legend": "Cena (EUR/MWh)",
            "step": 4,
            "tooltip": "Cena (EUR/MWh)"
        },
        "y2": {
            "decimals": 0,
            "legend": "Mno\u017estv\u00ed (MWh)",
            "step": 4,
            "tooltip": "Mno\u017estv\u00ed (MWh)"
        }
    },
    "data": {
        "dataLine": [
            {
                "bold": false,
                "colour": "FF6600",
                "point": [
                    {
                        "x": "1",
                        "y": 2557.8
                    },
                    {
                        "x": "2",
                        "y": 2026.4
                    },
                    {
                        "x": "3",
                        "y": 1518.2
                    },
                    {
                        "x": "4",
                        "y": 1595.5
                    },
                    {
                        "x": "5",
                        "y": 1503.5
                    },
                    {
                        "x": "6",
                        "y": 2369.5
                    },
                    {
                        "x": "7",
                        "y": 2804.3
                    },
                    {
                        "x": "8",
                        "y": 2789.9
                    },
                    {
                        "x": "9",
                        "y": 2759.5
                    },
                    {
                        "x": "10",
                        "y": 3001.5
                    },
                    {
                        "x": "11",
                        "y": 2893.8
                    },
                    {
                        "x": "12",
                        "y": 2906.7
                    },
                    {
                        "x": "13",
                        "y": 2743.6
                    },
                    {
                        "x": "14",
                        "y": 2563.9
                    },
                    {
                        "x": "15",
                        "y": 2634.3
                    },
                    {
                        "x": "16",
                        "y": 2473.0
                    },
                    {
                        "x": "17",
                        "y": 2447.5
                    },
                    {
                        "x": "18",
                        "y": 2465.1
                    },
                    {
                        "x": "19",
                        "y": 2787.6
                    },
                    {
                        "x": "20",
                        "y": 2728.0
                    },
                    {
                        "x": "21",
                        "y": 2991.2
                    },
                    {
                        "x": "22",
                        "y": 2942.3
                    },
                    {
                        "x": "23",
                        "y": 2910.2
                    },
                    {
                        "x": "24",
                        "y": 2596.0
                    }
                ],
                "title": "Mno\u017estv\u00ed (MWh)",
                "tooltip": "Mno\u017estv\u00ed",
                "tooltipDecimalsY": 1,
                "type": "2",
                "useTooltip": true,
                "useY2": true
            },
            {
                "bold": false,
                "colour": "A04000",
                "point": [
                    {
                        "x": "1",
                        "y": 77.0
                    },
                    {
                        "x": "2",
                        "y": 80.19
                    },
                    {
                        "x": "3",
                        "y": 61.15
                    },
                    {
                        "x": "4",
                        "y": 61.71
                    },
                    {
                        "x": "5",
                        "y": 60.01
                    },
                    {
                        "x": "6",
                        "y": 78.25
                    },
                    {
                        "x": "7",
                        "y": 132.12
                    },
                    {
                        "x": "8",
                        "y": 160.0
                    },
                    {
                        "x": "9",
                        "y": 155.22
                    },
                    {
                        "x": "10",
                        "y": 170.01
                    },
                    {
                        "x": "11",
                        "y": 152.78
                    },
                    {
                        "x": "12",
                        "y": 144.62
                    },
                    {
                        "x": "13",
                        "y": 137.25
                    },
                    {
                        "x": "14",
                        "y": 139.79
                    },
                    {
                        "x": "15",
                        "y": 135.0
                    },
                    {
                        "x": "16",
                        "y": 121.85
                    },
                    {
                        "x": "17",
                        "y": 122.77
                    },
                    {
                        "x": "18",
                        "y": 134.84
                    },
                    {
                        "x": "19",
                        "y": 147.05
                    },
                    {
                        "x": "20",
                        "y": 142.34
                    },
                    {
                        "x": "21",
                        "y": 143.58
                    },
                    {
                        "x": "22",
                        "y": 113.32
                    },
                    {
                        "x": "23",
                        "y": 102.7
                    },
                    {
                        "x": "24",
                        "y": 80.56
                    }
                ],
                "title": "Cena (EUR/MWh)",
                "tooltip": "Cena",
                "tooltipDecimalsY": 2,
                "type": "1",
                "useTooltip": true,
                "useY2": false
            }
        ]
    },
    "graph": {
        "fullscreen": true,
        "title": "V\u00fdsledky denn\u00edho trhu - 12.01.2023",
        "zoom": true
    }
}
        '''), client, local_tz.localize((datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)))
    else:
        d = local_tz.localize((datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))
        if (c["debug"]): print(d)
        send_to_mqtt(_request(d), client, d)


if __name__ == '__main__':
    run()
