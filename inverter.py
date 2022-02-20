import asyncio
import goodwe
from config import influxConfig, inverterConfig
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


async def store_runtime_data():
    client = InfluxDBClient(url=influxConfig["url"], token=influxConfig["token"], org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    inverter = await goodwe.connect(inverterConfig["ip_address"])
    runtime_data = await inverter.read_runtime_data()

    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("string", "1").field("power", runtime_data["ppv1"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("string", "2").field("power", runtime_data["ppv2"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("power", runtime_data["ppv"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("direction", runtime_data["grid_in_out_label"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("load", runtime_data["load_ptotal"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("in", runtime_data["e_day_imp"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "today").field("out", runtime_data["e_day_exp"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("in", runtime_data["e_total_imp"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").tag("sum", "total").field("out", runtime_data["e_total_exp"]))
    write_api.write(bucket=influxConfig["bucket"], record= Point("FVE").field("soc", runtime_data["battery_soc"]))

#    for sensor in inverter.sensors():
#        if sensor.id_ in runtime_data:
#            print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")


asyncio.run(store_runtime_data())