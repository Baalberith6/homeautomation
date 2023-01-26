import json
from datetime import datetime
from pprint import pprint

from dateutil import parser

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from config import influxConfig
from secret import influxToken, solcastKey
from config import generalConfig as c


def _request():
    r = requests.get('https://api.solcast.com.au/rooftop_sites/9a34-5411-4c58-3c98/forecasts?format=json&api_key=' + solcastKey)
    pprint (r.json())
    return r.json()


def store_runtime_data(r):
    client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    daily_sum = 0
    daily_sum_p10 = 0
    daily_sum_p90 = 0
    for estimate in r["forecasts"]:
        timestamp = parser.parse(estimate["period_end"])
        if timestamp.date() == datetime.today().date():
            daily_sum += estimate["pv_estimate"]
            daily_sum_p10 += estimate["pv_estimate10"]
            daily_sum_p90 += estimate["pv_estimate90"]
            if c["debug"]:
                print(timestamp, estimate["pv_estimate"])
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_50p", float(estimate["pv_estimate"])).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_10p", float(estimate["pv_estimate10"])).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_90p", float(estimate["pv_estimate90"])).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_50p_cummulative", float(daily_sum)).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_10p_cummulative", float(daily_sum_p10)).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_90p_cummulative", float(daily_sum_p90)).time(timestamp))


def run():
    if (c["debug"]):
        store_runtime_data(json.loads('''
{
    "forecasts":
    [
        {
            "pv_estimate": 0.6728,
            "pv_estimate10": 0.3385,
            "pv_estimate90": 1.2423,
            "period_end": "2023-01-25T10:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.4744,
            "pv_estimate10": 0.3679,
            "pv_estimate90": 0.5913,
            "period_end": "2023-01-25T10:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.5165,
            "pv_estimate10": 0.3566,
            "pv_estimate90": 0.9679,
            "period_end": "2023-01-25T11:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.5165,
            "pv_estimate10": 0.3494,
            "pv_estimate90": 1.5587,
            "period_end": "2023-01-25T11:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.5165,
            "pv_estimate10": 0.3494,
            "pv_estimate90": 2.1432,
            "period_end": "2023-01-25T12:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.6212,
            "pv_estimate10": 0.3057,
            "pv_estimate90": 4.2322,
            "period_end": "2023-01-25T12:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.7371,
            "pv_estimate10": 0.2547,
            "pv_estimate90": 3.2472,
            "period_end": "2023-01-25T13:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.8757,
            "pv_estimate10": 0.2402,
            "pv_estimate90": 2.3762,
            "period_end": "2023-01-25T13:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.8642,
            "pv_estimate10": 0.2402,
            "pv_estimate90": 2.775,
            "period_end": "2023-01-25T14:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.5913,
            "pv_estimate10": 0.1913,
            "pv_estimate90": 2.4932,
            "period_end": "2023-01-25T14:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.3164,
            "pv_estimate10": 0.1177,
            "pv_estimate90": 1.8358,
            "period_end": "2023-01-25T15:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.119,
            "pv_estimate10": 0.0446,
            "pv_estimate90": 0.5921,
            "period_end": "2023-01-25T15:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0.0075,
            "period_end": "2023-01-25T16:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T16:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T17:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T17:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T18:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T18:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T19:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T19:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T20:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T20:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T21:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T21:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T22:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T22:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T23:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-25T23:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T00:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T00:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T01:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T01:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T02:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T02:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T03:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T03:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T04:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T04:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T05:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T05:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T06:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T06:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.015,
            "pv_estimate10": 0.0075,
            "pv_estimate90": 0.0226,
            "period_end": "2023-01-26T07:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.1429,
            "pv_estimate10": 0.0827,
            "pv_estimate90": 0.2257,
            "period_end": "2023-01-26T07:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.331,
            "pv_estimate10": 0.1956,
            "pv_estimate90": 0.5543,
            "period_end": "2023-01-26T08:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.6601,
            "pv_estimate10": 0.3611,
            "pv_estimate90": 0.9988,
            "period_end": "2023-01-26T08:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0104,
            "pv_estimate10": 0.6131,
            "pv_estimate90": 1.4378,
            "period_end": "2023-01-26T09:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.2536,
            "pv_estimate10": 0.7772,
            "pv_estimate90": 1.7805,
            "period_end": "2023-01-26T09:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.3688,
            "pv_estimate10": 0.859,
            "pv_estimate90": 1.9731,
            "period_end": "2023-01-26T10:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.4493,
            "pv_estimate10": 0.9173,
            "pv_estimate90": 2.086,
            "period_end": "2023-01-26T10:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.5066,
            "pv_estimate10": 0.9523,
            "pv_estimate90": 2.131,
            "period_end": "2023-01-26T11:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.4263,
            "pv_estimate10": 0.894,
            "pv_estimate90": 2.0183,
            "period_end": "2023-01-26T11:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.2305,
            "pv_estimate10": 0.7538,
            "pv_estimate90": 1.7577,
            "period_end": "2023-01-26T12:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1148,
            "pv_estimate10": 0.6835,
            "pv_estimate90": 1.5981,
            "period_end": "2023-01-26T12:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0801,
            "pv_estimate10": 0.6835,
            "pv_estimate90": 1.5066,
            "period_end": "2023-01-26T13:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0104,
            "pv_estimate10": 0.6718,
            "pv_estimate90": 1.3688,
            "period_end": "2023-01-26T13:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.8357,
            "pv_estimate10": 0.5778,
            "pv_estimate90": 1.138,
            "period_end": "2023-01-26T14:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.5543,
            "pv_estimate10": 0.3761,
            "pv_estimate90": 0.7889,
            "period_end": "2023-01-26T14:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.3009,
            "pv_estimate10": 0.2257,
            "pv_estimate90": 0.401,
            "period_end": "2023-01-26T15:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.1128,
            "pv_estimate10": 0.0903,
            "pv_estimate90": 0.1504,
            "period_end": "2023-01-26T15:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0.0075,
            "period_end": "2023-01-26T16:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T16:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T17:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T17:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T18:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T18:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T19:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T19:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T20:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T20:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T21:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T21:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T22:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T22:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T23:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-26T23:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T00:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T00:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T01:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T01:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T02:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T02:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T03:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T03:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T04:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T04:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T05:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T05:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T06:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T06:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.0145,
            "pv_estimate10": 0.0072,
            "pv_estimate90": 0.0217,
            "period_end": "2023-01-27T07:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.143,
            "pv_estimate10": 0.0929,
            "pv_estimate90": 0.2145,
            "period_end": "2023-01-27T07:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.3289,
            "pv_estimate10": 0.2145,
            "pv_estimate90": 0.5369,
            "period_end": "2023-01-27T08:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.6366,
            "pv_estimate10": 0.3646,
            "pv_estimate90": 0.978,
            "period_end": "2023-01-27T08:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9389,
            "pv_estimate10": 0.5874,
            "pv_estimate90": 1.3515,
            "period_end": "2023-01-27T09:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1024,
            "pv_estimate10": 0.6536,
            "pv_estimate90": 1.6095,
            "period_end": "2023-01-27T09:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1132,
            "pv_estimate10": 0.5984,
            "pv_estimate90": 1.695,
            "period_end": "2023-01-27T10:00:00.0000000Z",
            "period": "PT30M"
        }
    ]
}
        '''))
    else:
        store_runtime_data(_request())


if __name__ == '__main__':
    run()
