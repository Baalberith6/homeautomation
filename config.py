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
    "stop_at_soc_diff": 3,
    "start_at_soc": 40,
}

azrouterConfig = {
    "ip_address": "http://192.168.1.167/",
}

wundergroundConfig = {
    "stationId": "ISTRMI2",
    "wait": 30
}

netatmoConfig = {
    "home_id": "65805d35c3db644204070181",
    "room_id_hala": "2965583580",
    "room_id_chodba": "297596189",
    "room_id_hostovska": "744850076",
    "room_id_julinka": "8060066",
    "room_id_kubo": "802684169",
    "room_id_kupelna": "1611437767",
    "room_id_spalna": "1440725479",
    "thermostat_id": "04:00:00:ae:79:6c",
}

rehauConfig = {
    "ip_address": "http://192.168.0.2/",
    "temp_hala": 20.0,
    "temp_all": 21.0
}

estiaConfig = {
    "consumer_id": "de7cb3cc-7895-4e7b-bafb-bb0550e124d8",
    "group_id": "f9982076-0cfe-4ee0-8e60-ef8a94e19e12",
    "device_id": "99daa6c3-687a-454b-b2a1-fd576686cb55",
    "device_unique_id": "11bc7715-82ea-49c4-9c19-c3fc8833de4e",
}

mqttConfig = {
    "broker": "localhost",
    "port": 1883
}

generalConfig = {
    "debug": False
}
