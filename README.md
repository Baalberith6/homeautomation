# Home Energy Automation

Home energy automation system built around MQTT and InfluxDB. Independent Python services monitor and control solar inverter, EV charger, heat pump, thermostats, and vehicles — optimizing for PV self-consumption and electricity price.

Architecture and device pages: `../kb/index.md`

## Setup

```bash
pip install -r requirements.txt
```

`secret.py` is a committed stub with empty values. Fill it on the host; do not commit the values.

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
