# Home Energy Automation

Home energy automation system built around MQTT and InfluxDB. Independent Python services monitor and control solar inverter, EV charger, heat pump, thermostats, and vehicles — optimizing for PV self-consumption and electricity price.

## Services

| Service | Role |
|---------|------|
| `inverter.py` | Reads GoodWe solar inverter (PV power, battery SOC, grid current) |
| `inverter_setter.py` | Dynamically adjusts battery charging curves based on SOC |
| `wallbox.py` | Controls go-eCharger EV charger current from PV surplus |
| `estia.py` | Reads Toshiba Estia heat pump via HTTP API |
| `estia_optimizer.py` | Schedules heat pump operation based on OTE electricity prices |
| `estia_energy.py` | Calculates heat pump COP, writes to InfluxDB |
| `netatmo.py` | Reads Netatmo thermostats (7 rooms), publishes temps and heating % |
| `skoda.py` / `car.py` | Reads Skoda/VW vehicle data (SOC, range, charging status) |
| `oteforecast.py` | Fetches Czech electricity spot prices from OTE |
| `solarforecast.py` | Fetches Solcast PV generation forecast |

## Infrastructure

- **MQTT broker**: `192.168.1.52:1883` — central message bus (`home/`, `bool/`, `command/`, `wallbox/`, `diag/` topics)
- **InfluxDB**: `192.168.1.50` — time-series storage
- **Telegraf**: bridges MQTT to InfluxDB (config backed up in `telegraf.conf`)
- **Grafana**: dashboards via InfluxDB + websocket live push

## Setup

```bash
pip install -r requirements.txt
cp secret.py.example secret.py  # fill in API keys and credentials
```

`secret.py` holds all API keys and credentials (not committed). See the committed stub for required variables.

`config.py` holds device IPs, MQTT/InfluxDB endpoints, device IDs, and polling intervals.

## Running

```bash
# Run a service
python3 inverter.py

# Run locally in debug mode (safe alongside prod)
DEBUG=1 python3 inverter.py
```

`DEBUG=1` enables verbose output and appends `-dev` to the MQTT client ID so the local instance doesn't disconnect production. Netatmo token files use a `.dev.token` suffix in debug mode.

**Warning:** Services that control devices (`wallbox.py`, `inverter_setter.py`, `estia_optimizer.py`) send real commands even in debug mode.

## Deployment

Services run as systemd units on `192.168.1.51`. Python file `foo.py` maps to unit `0-foo.service`.

```bash
./deploy.sh <service>        # git pull, restart unit, tail logs
./deploy.sh <service> 15     # override wait seconds (default 8)
```

## Tests

```bash
flake8                  # lint
pytest tests/           # all tests
pytest tests/file.py    # single file
```

CI runs on every push (`.github/workflows/test.yaml` — Python 3.9, flake8 + pytest).
