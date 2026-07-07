influxConfig = {
    "url": "http://192.168.1.50:8086",
    "org": "Home",
    "bucket": "default",
}

inverterConfig = {
    "ip_address": "192.168.10.77",
    "wait": 5
}

wallboxConfig = {
    "address": "http://192.168.1.201/"
}

wundergroundConfig = {
    "stationId": "ISTRMI2",
    "wait": 30
}

skodaConfig = {
    "vin_skoda": "TMBJC9NY2NF008913",
    "vin_vw": "WVWZZZE11S8005795",
}

# VW EU Data Act portal. VW shut down the online API the carconnectivity
# library used, so the ID.3 is now read from the mandated self-service data
# portal (a ~15-min ZIP export) instead. Credentials are reused from
# carConnectivityConfig (VW ID == MySkoda account). See vw_euda.py.
vwEudaConfig = {
    "identity_base": "https://identity.vwgroup.io",
    "base_url": "https://eu-data-act.drivesomethinggreater.com",
    "client_id": "9b58543e-1c15-4193-91d5-8a14145bebb0@apps_vw-dilab_com",
    "scope": "openid cars profile",
    "brand": "VOLKSWAGEN_PASSENGER_CARS",
    "country": "cz",
    "language": "en",
    "cookie_file": "vw_euda_cookies.pickle",
    "poll_interval": 60,    # seconds — tick every 1 min; download only new files
    "merge_files": 6,       # on startup, seed state from the N newest ZIPs
    # Live SoC interpolation between the ~15-min portal drops.
    "capacity_kwh": 75,     # usable HV battery capacity (0->100%)
    "charge_efficiency": 0.9,  # charge_power is AC-side; battery gets ~90%
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
    "ip_address": "http://192.168.0.2/"
}

estiaConfig = {
    "consumer_id": "de7cb3cc-7895-4e7b-bafb-bb0550e124d8",
    "group_id": "f9982076-0cfe-4ee0-8e60-ef8a94e19e12",
    "device_id": "99daa6c3-687a-454b-b2a1-fd576686cb55",
    "device_unique_id": "11bc7715-82ea-49c4-9c19-c3fc8833de4e",
}

cezConfig = {
    "supply_point_uid": "0000758050742000836853859182400104557955",
    "partner_id": "0020834670",
}

mqttConfig = {
    "broker": "192.168.1.52",
    "port": 1883
}

grafanaConfig = {
    "ip_address": "http://192.168.1.50:3000/",
    "dashboard_id": "q50mEhf7k"
}

cursorConfig = {
    "team_id": "10101757"
}

moesCo2Config = {
    "device_id": "bf9e59a6b0884394eflzhf",
    "api_region": "eu",
    "update_interval": 60  # seconds
}

import os

generalConfig = {
    "debug": os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
}

