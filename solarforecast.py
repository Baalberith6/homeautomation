from datetime import datetime
from dateutil.parser import parse

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from config import influxConfig
from secret import influxToken
from config import generalConfig as c


def _request():
    r = requests.get('https://api.forecast.solar/estimate/49.1503508/15.2338656/25/19/9.9')
    return r.json()


def store_runtime_data(r):
    client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    for key in r["result"]["watt_hours_period"].keys():
        if parse(key).date() == datetime.today().date():
            if c["debug"]:
                print(parse(key), r["result"]["watt_hours_period"][key])
            write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("hourly", r["result"]["watt_hours_period"][key]).time(int(parse(key).timestamp())))

    for key in r["result"]["watt_hours_day"].keys():
        if c["debug"]:
            print(parse(key).timestamp(), r["result"]["watt_hours_day"][key])
        write_api.write(bucket=influxConfig["bucket"], record=Point("SolarForecast").field("daily", r["result"]["watt_hours_day"][key]).time(int(parse(key).timestamp())))
        break


def run():
    store_runtime_data(_request())


if __name__ == '__main__':
    run()
