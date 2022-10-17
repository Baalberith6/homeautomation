# homeautomation

## Telegraph setup
`telegraph.conf`

```
[[inputs.mqtt_consumer]]
  servers = ["tcp://127.0.0.1:1883"]

  topics = [
    "home/#",
  ]
  
  topic_tag = "" ## The message topic will be stored in a tag
  qos = 2 ## 0 = at most once, 1 = at least once, 2 = exactly once
  persistent_session = true ## To receive messages that arrived while the client is offline, needs QoS and client_id
  client_id = "telegraph-1"
  # username = "anonymous"
  # password = "metricsmetricsmetricsmetrics"
  data_format = "value" ## https://github.com/influxdata/telegraf/blob/master/docs/DATA_FORMATS_INPUT.md
  data_type = "float"

  ## Enable extracting tag values from MQTT topics
  ## _ denotes an ignored entry in the topic path
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/weather/forecast/yr/+"
    measurement = "_/measurement/_/_/_"
    tags = "_/_/_/service/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/weather/local/+"
    measurement = "_/measurement/_/_"
    tags = "_/_/_/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/weather/sensors/+"
    measurement = "_/measurement/_/_"
    tags = "_/_/_/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/Car/+"
    measurement = "_/measurement/_"
    tags = "_/_/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/FVE/power/+"
    measurement = "_/measurement/_/_"
    tags = "_/_/power/string"
    [[processors.pivot]]
      tag_key = "power"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/FVE/curr/+"
    measurement = "_/measurement/_/_"
    tags = "_/_/curr/phase"
    [[processors.pivot]]
      tag_key = "curr"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/FVE/battery/+/+"
    measurement = "_/measurement/_/_/_"
    tags = "_/_/_/sum/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "home/FVE/+"
    measurement = "_/measurement/_"
    tags = "_/_/field"
    [[processors.pivot]]
      tag_key = "field"
      value_key = "value"
```

```
[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "TOKEN FROM Influx UI -> Data -> API Tokens"
  organization = "Home"
  bucket = "mqtt"
```