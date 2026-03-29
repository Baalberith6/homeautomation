# go-eCharger API Specification (english version)

**This documentation is valid for firmware version of the adapter 033**

# Index

1. [Connection](#1-connection-)
   - [Rate Limiting](#rate-limiting)
2. [API: status](#2-api-status-)
   - [Request Path](#request-path)
   - [Return Format](#return-format)
   - [Parameter](#parameter)
3. [Commands](#3-commands-)
   - [Set parameter](#set-parameter)
   - [Path](#path)
4. [Return Values](#4-return-values-)
   - [Local WiFi / Hotspot](#local-wifi--hotspot)
   - [Cloud: REST Api](#cloud-rest-api)
5. [Cloud REST Api Workflow](#5-cloud-rest-api-workflow-)
6. [Custom MQTT Server](#6-custom-mqtt-server-)

# 1. Connection:

The go-eCharger offers two WLAN interfaces, one of which always serves as a mobile hotspot
and another that can connect to an existing WLAN network to establish an Internet connection.

| Connection         | Path                                                             |
| ------------------ | ---------------------------------------------------------------- |
| WiFi Hotspot       | http://192.168.4.1/                                              |
| WiFi local network | http://x.x.x.x/ The IP address is retrieved from the DHCP server |
| Cloud: REST Api    | https://api.go-e.co/                                             |
| Custom MQTT Server |                                                                  |

Authentication:

| Connection         | Authentication                                                                                     |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| WiFi Hotspot       | None (Hotspot WPA key must be known)                                                               |
| WiFi local network | None (device must be in the same WLAN and the HTTP Api must be activated with the go-eCharger app) |
| Cloud: REST Api    | go-eCharger Cloud Token                                                                            |
| Custom MQTT Server | None                                                                                               |

### Rate Limiting

| Connection         | Limit                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WiFi Hotspot       | None (5 second delay recommended)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| WiFi local network | None (5 second delay recommended)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Cloud: REST Api    | **Fair use Limit**: 50MB per month, about 500'000 requests. |
| Custom MQTT Server | None (5 second delay recommended)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

# 2. API: status:

Returns all relevant parameters as a JSON object.

### Request Path

| Connection         | Path                                                                                    |
| ------------------ | --------------------------------------------------------------------------------------- |
| WiFi Hotspot       | http://192.168.4.1/status                                                               |
| WiFi local network | http://x.x.x.x/status                                                                   |
| Cloud: REST Api    | https://api.go-e.co/api_status?token=TOKEN [&wait=0]                                    |

### Parameter

| Parameter | Format     | Explanation |
| --------- | ---------- | ----------- |
| version   | String (1) | **JSON Format.** "B": normal case, "C": end-to-end encryption enabled |
| rbc       | uint32_t   | **reboot_counter:** Counts boot operations. |
| rbt       | uint32_t   | **reboot_timer:** Milliseconds since last boot. Expires after 49 days. |
| car       | uint8_t    | **Status PWM Signaling** 1: charging station ready, no vehicle. 2: vehicle loads. 3: Waiting for vehicle. 4: Charge finished, vehicle still connected |
| amp       | uint8_t    | Ampere value for PWM signaling **6-32A** |
| amx       | uint8_t    | Ampere value for PWM signaling **6-32A** (not written to flash, resets on reboot). Recommended for PV charging |
| err       | uint8_t    | **error:** 1: RCCB, 3: PHASE, 8: NO_GROUND, 10: INTERNAL (default) |
| ast       | uint8_t    | **access_state:** 0: open, 1: RFID/App needed, 2: electricity price/automatic |
| alw       | uint8_t    | **allow_charging:** PWM signal may be present. 0: no, 1: yes |
| stp       | uint8_t    | **stop_state:** 0: deactivated, 2: switch off after kWh |
| cbl       | uint8_t    | **Typ2 Cable Ampere encoding** 13-32: Ampere, 0: no cable |
| pha       | uint8_t    | **Phases** before/after contactor. Binary flags: 0b00ABCDEF (A-C: before, D-F: after) |
| tmp       | uint8_t    | **Temperature** of controller in °C |
| dws       | uint32_t   | **Charged energy** in deca-watt seconds (100000 = 277Wh) |
| dwo       | uint16_t   | **Shutdown value** in 0.1kWh if stp==2 |
| adi       | uint8_t    | **adapter_in:** 0: NO_ADAPTER, 1: 16A_ADAPTER |
| uby       | uint8_t    | **unlocked_by:** RFID card number that activated current charging |
| eto       | uint32_t   | **energy_total:** Total charged energy in 0.1kWh |
| wst       | uint8_t    | **wifi_state:** 3: connected, default: not connected |
| nrg       | array[15]  | Current/voltage sensor array. [0-2]: L1-L3 voltage (V). [3]: N voltage. [4-6]: L1-L3 current (0.1A). [7-9]: L1-L3 power (0.1kW). [10]: N power. [11]: Total power (0.01kW). [12-15]: Power factors L1-L3,N (%) |
| fwv       | String     | **Firmware Version** |
| sse       | String     | **Serial number** (%06d format) |
| wss       | String     | WiFi **SSID** |
| wke       | String     | WiFi **Key** |
| wen       | uint8_t    | **wifi_enabled:** 0: deactivated, 1: activated |
| tof       | uint8_t    | **time_offset:** Timezone in hours +100 (101 = GMT+1) |
| tds       | uint8_t    | **Daylight saving time offset** in hours |
| lbr       | uint8_t    | **LED brightness** 0-255 |
| aho       | uint8_t    | Min hours to load with electricity price automatic |
| afi       | uint8_t    | Hour by which aho hours must be charged |
| azo       | uint8_t    | Awattar price zone. 0: Austria, 1: Germany |
| ama       | uint8_t    | **Absolute max Ampere** |
| al1-al5   | uint8_t    | Ampere levels 1-5 for device push button |
| cid       | uint24_t   | Color idle (standby, no car) |
| cch       | uint24_t   | Color charging active |
| cfi       | uint24_t   | Color charging finished |
| lse       | uint8_t    | **led_save_energy:** Auto LED off after 10s. 0: off, 1: on |
| ust       | uint8_t    | **unlock_state:** 0: locked while plugged, 1: unlock after charge, 2: always locked |
| wak       | String     | WiFi **Hotspot Password** |
| r1x       | uint8_t    | **Flags** 0b1: HTTP API enabled, 0b10: E2E encryption |
| dto       | uint8_t    | **Remaining time** in ms on electricity price activation |
| nmo       | uint8_t    | **Norway mode** 0: off (earthing detection on), 1: on (IT grids) |
| eca-ec1   | uint32_t   | Charged **energy per RFID card** 1-10 |
| rca-rc1   | String     | **RFID Card ID** 1-10 |
| rna-rn1   | String     | **RFID Card Name** 1-10 (max 10 chars) |
| tme       | String     | **Current time** (ddmmyyhhmm) |
| sch       | String     | **Scheduler settings** (base64 encoded) |
| sdp       | uint8_t    | **Scheduler double press** 0: disabled, 1: allow immediate charge |
| upd       | uint8_t    | **Update available** 0: no, 1: yes |
| cdi       | uint8_t    | **Cloud disabled** 0: enabled, 1: disabled |
| loe       | uint8_t    | **Load balancing enabled** 0: off, 1: on via cloud |
| lot       | uint8_t    | **Load balancing group total ampere** |
| lom       | uint8_t    | **Load balancing minimum amperage** |
| lop       | uint8_t    | **Load balancing priority** |
| log       | String     | **Load balancing group ID** |
| lon       | uint8_t    | **Load balancing expected stations** (not supported) |
| lof       | uint8_t    | **Load balancing fallback amperage** |
| loa       | uint8_t    | **Load balancing Ampere** (auto controlled) |
| lch       | uint32_t   | **Load balancing: seconds since last current flow** (0 when charging) |
| mce       | uint8_t    | **MQTT custom enabled** 0: off, 1: on |
| mcs       | String(63) | **MQTT custom Server** hostname |
| mcp       | uint16_t   | **MQTT custom Port** |
| mcu       | String(16) | **MQTT custom Username** |
| mck       | String(16) | **MQTT custom Key** |
| mcc       | uint8_t    | **MQTT custom connected** 0: no, 1: yes |

# 3. Commands:

Read-only parameters:
```
version rbc rbt car err cbl pha tmp dws adi uby eto wst nrg fwv sse eca ecr
ecd ec4 ec5 ec6 ec7 ec8 ec9 ec1 rca rcr rcd rc4 rc5 rc6 rc7 rc8 rc9 rc1
```

Settable parameters:
```
amp amx ast alw stp dwo wss wke wen tof tds lbr aho afi ama al1 al2 al3 al4 al5
cid cch cfi lse ust wak r1x dto nmo rna rnm rne rn4 rn5 rn6 rn7 rn8 rn9 rn1
```

### Set parameter

Format: `[param]=[value]` (e.g. `amp=16`)

| Connection         | Path                                                        |
| ------------------ | ----------------------------------------------------------- |
| WiFi Hotspot       | http://192.168.4.1/mqtt?payload=                            |
| WiFi local network | http://x.x.x.x/mqtt?payload=                                |
| Cloud: REST Api    | https://api.go-e.co/api?token=TOKEN&payload=MESSAGE          |

# 6. Custom MQTT Server:

From firmware version 030 on, a separate MQTT server can be used.

Commands topic: **go-eCharger/000000/cmd/req** (replace 000000 with serial number)

Status topic: **go-eCharger/000000/status** (published every 5 seconds)
