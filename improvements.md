# Improvements

## ~~P0 — Broken now~~ ✓ all fixed

### ~~1. `inverter_setter.py` cannot start~~ ✓ fixed
Merged duplicate tracking variables into `last_curr_set`, removed dead `handle_inverter_battery_discharge_current()` and `discharging_curve()`.

---

## P1 — Silent failures / safety risk

### ~~2. No resilience in main loops~~ ✓ fixed
All `while True:` loops now have `try/except` inside the loop body. On error the service prints the exception and continues after the normal sleep interval. Covers: `estia.py`, `inverter.py`, `netatmo.py`, `rehau.py`, `yr.py`, `co2.py`, `car.py`, `skoda.py`.

### 3. No health monitoring
No service publishes a liveness signal. If `wallbox.py` silently dies, PV-optimized EV charging stops with no alert. Each service should publish to `diag/<service>/heartbeat` periodically. Grafana can alert on stale heartbeats.

### ~~4. Unit tests for safety-critical control logic~~ ✓ fixed
Added tests for all services: resilience (13 tests), estia hex parsing/TUV logic (18), inverter diagnostics filtering (8), car charging time/VIN routing (9), netatmo file I/O/heating power (9). Also fixed 2 pre-existing broken tests (`energyestimator_unit_test.py`, `estia_optimizer_unit_test.py`). Total: 94 tests, all passing. `inverter_setter.py` charging curves remain untested.

---

## P2 — Operational hygiene

### 5. systemd unit files
No process supervisor config in the repo. Commit a `systemd/` directory with `.service` files per long-running script for:
- `Restart=on-failure` (automatic restart)
- `After=network-online.target mosquitto.service influxdb.service` (correct ordering)
- `journalctl -u wallbox` (per-service logs)

### 6. Structured logging
~50+ scattered `if c["debug"]: print(...)` calls — all-or-nothing, no severity levels, no timestamps. Switch to Python's `logging` module with `DEBUG`/`INFO`/`WARNING` levels per module. Enables easy redirect to Loki/Grafana.

### 7. Hardcoded wallbox serial in topic
`wallbox.py:233` subscribes to `go-eCharger/201630/#` and publishes to the same prefix on lines 138, 150, 151, 160, 168. The serial `201630` should be in `wallboxConfig`.

### ~~8. MQTT v3/v5 mismatch in `common.py`~~ ✓ fixed
Switched client to MQTTv5 so `MessageExpiryInterval` is actually applied by the broker.

---

## P3 — Architecture (plan, don't rush)

### 9. Containerize services on Proxmox
All services share one Python environment and one `requirements.txt`. A dependency upgrade can break unrelated scripts. Natural split into Docker Compose groups or separate LXCs:
- **Energy bus**: `inverter.py`, `inverter_setter.py`, `wallbox.py`
- **Climate**: `estia.py`, `estia_energy.py`, `netatmo.py`
- **Forecasting**: `oteforecast.py`, `solarforecast.py`, `estia_optimizer.py`
- **Vehicles**: `car.py`, `skoda.py`

### 10. Secret management
`secret.py` stores all credentials as plain Python. Switch to environment variables loaded from `.env` via `python-dotenv` — same codebase across dev/prod, no credentials in the repo.

---

## Removed from previous list

### ~~Thread safety around global state~~
Previously listed as a concern for `wallbox.py` and `inverter_setter.py`. Both use `loop_forever()`, which runs all MQTT callbacks in a single thread — there is no concurrency issue. No fix needed.
