import time
import tinytuya

from common import connect_mqtt, publishProperties
from config import moesCo2Config, generalConfig as c
from secret import tuyaApiKey, tuyaApiSecret


class MOESCo2Sensor:
    def __init__(self, device_id):
        self.device_id = device_id
        self.client = None
        self.last_co2 = None
        
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        self.client = connect_mqtt("moes_co2_sensor")
        self.client.loop_start()
        
    def get_co2_value(self):
        """Get CO2 value from MOES sensor using tinytuya"""
        try:
            # Create tinytuya device instance
            device = tinytuya.Cloud(
                apiRegion=moesCo2Config["api_region"],
                apiKey=tuyaApiKey,
                apiSecret=tuyaApiSecret,
                apiDeviceID=self.device_id
            )
            
            # Get device status
            status = device.getstatus(self.device_id)
            
            if c["debug"]:
                print(f"Device status: {status}")
            
            # Extract CO2 value from status
            if 'result' in status and isinstance(status['result'], list):
                result_list = status['result']
                
                # Look for co2_value in the result list
                co2_value = None
                for item in result_list:
                    if isinstance(item, dict) and 'code' in item and 'value' in item:
                        if item['code'] == 'co2_value':
                            co2_value = item['value']
                            break
                
                if co2_value is not None:
                    return float(co2_value)
                else:
                    if c["debug"]:
                        print(f"CO2 value not found in result list: {result_list}")
                    return None
            else:
                if c["debug"]:
                    print(f"No result list in status: {status}")
                return None
                
        except Exception as e:
            if c["debug"]:
                print(f"Error getting CO2 value: {e}")
            return None
    
    def publish_co2_data(self, co2_value):
        """Publish CO2 data to MQTT topic"""
        if self.client is None or co2_value is None:
            return
            
        # Only publish if value has changed
        if co2_value != self.last_co2:
            self.client.publish(
                "home/weather/sensors/moes_co2", 
                co2_value, 
                qos=2, 
                properties=publishProperties
            )
            self.last_co2 = co2_value
            if c["debug"]:
                print(f"Published CO2: {co2_value} ppm")
    
    def run(self):
        """Main loop for the sensor"""
        self.connect_mqtt()
        
        if c["debug"]:
            print("MOES CO2 Sensor started. Polling for CO2 data...")
        
        try:
            while True:
                # Get CO2 value from sensor
                co2_value = self.get_co2_value()
                
                # Publish to MQTT
                self.publish_co2_data(co2_value)
                
                # Wait before next reading
                time.sleep(moesCo2Config["update_interval"])
                
        except KeyboardInterrupt:
            if c["debug"]:
                print("Stopping MOES CO2 Sensor...")
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()


def main():
    device_id = moesCo2Config["device_id"]
    sensor = MOESCo2Sensor(device_id)
    sensor.run()


if __name__ == "__main__":
    main()