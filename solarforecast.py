import json
from datetime import datetime, timedelta
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
    return r.json()


def store_runtime_data(r):
    client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    daily_sum = 0
    daily_sum_p10 = 0
    daily_sum_p90 = 0
    for estimate in r["forecasts"]:
        timestamp = parser.parse(estimate["period_end"]) - timedelta(minutes=5) # so it is not counted towards next interval
        if timestamp.date() == datetime.today().date():
            daily_sum += estimate["pv_estimate"]/2
            daily_sum_p10 += estimate["pv_estimate10"]/2
            daily_sum_p90 += estimate["pv_estimate90"]/2
            if c["debug"]:
                print(timestamp, estimate["pv_estimate"]/2)
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_50p", float(estimate["pv_estimate"]/2)).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_10p", float(estimate["pv_estimate10"]/2)).time(timestamp))
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("30m_90p", float(estimate["pv_estimate90"]/2)).time(timestamp))
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
            "pv_estimate": 0.6005,
            "pv_estimate10": 0.4131,
            "pv_estimate90": 0.8449,
            "period_end": "2023-01-27T08:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9376,
            "pv_estimate10": 0.6705,
            "pv_estimate90": 1.2256,
            "period_end": "2023-01-27T09:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0992,
            "pv_estimate10": 0.7752,
            "pv_estimate90": 1.443,
            "period_end": "2023-01-27T09:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0992,
            "pv_estimate10": 0.752,
            "pv_estimate90": 1.5,
            "period_end": "2023-01-27T10:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0807,
            "pv_estimate10": 0.7115,
            "pv_estimate90": 1.5142,
            "period_end": "2023-01-27T10:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0693,
            "pv_estimate10": 0.6767,
            "pv_estimate90": 1.5255,
            "period_end": "2023-01-27T11:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0118,
            "pv_estimate10": 0.607,
            "pv_estimate90": 1.4688,
            "period_end": "2023-01-27T11:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9197,
            "pv_estimate10": 0.5255,
            "pv_estimate90": 1.3551,
            "period_end": "2023-01-27T12:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.862,
            "pv_estimate10": 0.5021,
            "pv_estimate90": 1.2639,
            "period_end": "2023-01-27T12:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.8504,
            "pv_estimate10": 0.5138,
            "pv_estimate90": 1.1839,
            "period_end": "2023-01-27T13:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.819,
            "pv_estimate10": 0.5318,
            "pv_estimate90": 1.104,
            "period_end": "2023-01-27T13:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.7127,
            "pv_estimate10": 0.5097,
            "pv_estimate90": 0.9368,
            "period_end": "2023-01-27T14:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.4709,
            "pv_estimate10": 0.3432,
            "pv_estimate90": 0.6385,
            "period_end": "2023-01-27T14:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.2645,
            "pv_estimate10": 0.2073,
            "pv_estimate90": 0.336,
            "period_end": "2023-01-27T15:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.1072,
            "pv_estimate10": 0.0786,
            "pv_estimate90": 0.1287,
            "period_end": "2023-01-27T15:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.0071,
            "pv_estimate10": 0,
            "pv_estimate90": 0.0071,
            "period_end": "2023-01-27T16:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T16:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T17:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T17:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T18:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T18:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T19:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T19:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T20:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T20:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T21:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T21:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T22:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T22:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T23:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-27T23:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T00:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T00:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T01:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T01:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T02:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T02:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T03:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T03:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T04:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T04:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T05:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T05:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T06:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T06:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.0146,
            "pv_estimate10": 0.0073,
            "pv_estimate90": 0.0292,
            "period_end": "2023-01-28T07:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.1389,
            "pv_estimate10": 0.0658,
            "pv_estimate90": 0.2412,
            "period_end": "2023-01-28T07:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.3143,
            "pv_estimate10": 0.1608,
            "pv_estimate90": 0.6039,
            "period_end": "2023-01-28T08:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.6152,
            "pv_estimate10": 0.2924,
            "pv_estimate90": 1.0619,
            "period_end": "2023-01-28T08:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9508,
            "pv_estimate10": 0.4574,
            "pv_estimate90": 1.492,
            "period_end": "2023-01-28T09:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1215,
            "pv_estimate10": 0.5316,
            "pv_estimate90": 1.7879,
            "period_end": "2023-01-28T09:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1766,
            "pv_estimate10": 0.5091,
            "pv_estimate90": 1.9389,
            "period_end": "2023-01-28T10:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1986,
            "pv_estimate10": 0.4866,
            "pv_estimate90": 2.0357,
            "period_end": "2023-01-28T10:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.2134,
            "pv_estimate10": 0.4821,
            "pv_estimate90": 2.0894,
            "period_end": "2023-01-28T11:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1805,
            "pv_estimate10": 0.4597,
            "pv_estimate90": 2.0467,
            "period_end": "2023-01-28T11:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.1039,
            "pv_estimate10": 0.4078,
            "pv_estimate90": 1.9274,
            "period_end": "2023-01-28T12:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.0483,
            "pv_estimate10": 0.4078,
            "pv_estimate90": 1.7861,
            "period_end": "2023-01-28T12:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9926,
            "pv_estimate10": 0.4305,
            "pv_estimate90": 1.6333,
            "period_end": "2023-01-28T13:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.9256,
            "pv_estimate10": 0.4531,
            "pv_estimate90": 1.4468,
            "period_end": "2023-01-28T13:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.7801,
            "pv_estimate10": 0.4078,
            "pv_estimate90": 1.1928,
            "period_end": "2023-01-28T14:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.521,
            "pv_estimate10": 0.2962,
            "pv_estimate90": 0.8361,
            "period_end": "2023-01-28T14:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.2889,
            "pv_estimate10": 0.1806,
            "pv_estimate90": 0.4418,
            "period_end": "2023-01-28T15:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.1156,
            "pv_estimate10": 0.0722,
            "pv_estimate90": 0.1734,
            "period_end": "2023-01-28T15:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.0073,
            "pv_estimate10": 0.0073,
            "pv_estimate90": 0.0073,
            "period_end": "2023-01-28T16:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T16:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T17:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T17:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T18:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T18:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T19:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T19:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T20:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T20:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T21:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T21:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T22:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T22:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T23:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-28T23:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T00:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T00:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T01:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T01:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T02:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T02:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T03:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T03:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T04:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T04:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T05:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T05:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T06:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0,
            "pv_estimate10": 0,
            "pv_estimate90": 0,
            "period_end": "2023-01-29T06:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.0386,
            "pv_estimate10": 0.0155,
            "pv_estimate90": 0.1856,
            "period_end": "2023-01-29T07:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.2937,
            "pv_estimate10": 0.1082,
            "pv_estimate90": 1.9433,
            "period_end": "2023-01-29T07:30:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 0.7177,
            "pv_estimate10": 0.2369,
            "pv_estimate90": 3.4695,
            "period_end": "2023-01-29T08:00:00.0000000Z",
            "period": "PT30M"
        },
        {
            "pv_estimate": 1.387,
            "pv_estimate10": 0.4256,
            "pv_estimate90": 4.4663,
            "period_end": "2023-01-29T08:30:00.0000000Z",
            "period": "PT30M"
        }
    ]
}
        '''))
    else:
        store_runtime_data(_request())


if __name__ == '__main__':
    run()
