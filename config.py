influxConfig = {
    "url": "http://localhost:8086",
    "org": "Home",
    "bucket": "default",
}

inverterConfig = {
    "ip_address": "192.168.1.77",
    "wait": 5
}

wallboxConfig = {
    "address": "http://192.168.1.200/",
    "stop_at_soc": 65,
    "start_at_soc": 75,
}

azrouterConfig = {
    "ip_address": "http://192.168.1.167/",
}

wundergroundConfig = {
    "stationId": "ISTRMI1",
    "wait": 30
}

mqttConfig = {
    "broker": "localhost",
    "port": 1883
}

generalConfig = {
    "debug": True
}