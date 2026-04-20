# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
flake8

# Run tests
pytest tests/

# Run a single test file
pytest tests/estia_optimizer_unit_test.py

# Run an individual service (example)
python3 inverter.py
python3 wallbox.py

# Run a service locally in debug mode (safe alongside prod)
DEBUG=1 python3 inverter.py
```

`DEBUG=1` enables verbose output and appends `-dev` to the MQTT client ID so the local instance doesn't disconnect the production one. Netatmo token files also use a `.dev.token` suffix to avoid overwriting prod tokens. **Caution:** services that control devices (`wallbox.py`, `inverter_setter.py`, `estia_optimizer.py`) will still send real commands — avoid running them locally while prod is active.

CI runs on every push via `.github/workflows/test.yaml` (Python 3.9, flake8 + pytest).

## Architecture

This is a home energy automation system built around **MQTT as the central message bus** with **InfluxDB for time-series storage**. Services are independent Python processes with no central orchestrator — they communicate via MQTT pub/sub topics under `home/`, `bool/`, `command/`, `wallbox/`, `jsons/`, `diag/` prefixes.

**Infrastructure:**
- MQTT broker: `192.168.1.52:1883` (configured in `config.py`)
- InfluxDB: `192.168.1.50` (configured in `config.py`)
- All credentials in `secret.py` (not committed)

**Key services and their roles:**

| File | Runs | Role |
|------|------|------|
| `inverter.py` | Continuous (5s) | Reads GoodWe solar inverter via LAN, publishes 40+ metrics (PV power, battery SOC, grid current) |
| `inverter_setter.py` | MQTT event-driven | Subscribes to inverter data, controls battery charging curves dynamically |
| `wallbox.py` | MQTT event-driven | Controls go-eCharger EV charger; computes allowable current from PV surplus + battery SOC |
| `estia.py` | Continuous (60s) | Reads Toshiba Estia heat pump via HTTP API, publishes to MQTT |
| `estia_energy.py` | Hourly at :22 | Calculates heat pump COP from temp history + hourly consumption, writes to InfluxDB |
| `netatmo.py` | Continuous (60s) | Reads 7-room Netatmo thermostats via OAuth2, publishes room temps and heating % |
| `car.py` / `skoda.py` | Continuous (120s) | Reads Skoda/VW vehicle data (SOC, range, charging status, GPS position) via CarConnectivity; reverse-geocodes address via Nominatim |
| `oteforecast.py` | Cron (hourly) | Fetches Czech electricity prices from OTE API, publishes to MQTT |
| `solarforecast.py` | Cron (hourly) | Fetches Solcast PV generation forecast, writes to InfluxDB |
| `cursor.py` | Cron (Mon 07:00 UTC) | Aggregates Cursor IDE analytics, writes to InfluxDB |

**Energy optimization flow:**
1. `inverter.py` publishes real-time PV production and battery SOC
2. `wallbox.py` subscribes and dynamically adjusts EV charging amps (maximizes PV self-consumption)
3. `inverter_setter.py` adjusts battery charge curves based on SOC thresholds
4. `oteforecast.py` + `solarforecast.py` provide price/generation forecasts for scheduling decisions
5. `estia_optimizer.py` uses OTE prices to schedule heat pump operation

**State management:** MQTT-based services use module-level global variables to persist state between messages (e.g., `soc`, `amp` in `wallbox.py`). Services rely on an external supervisor (systemd/supervisord) for restart-on-failure.

**OAuth tokens:** Netatmo tokens are persisted to `netatmo.token` and `netatmo_optimizer.token` on disk and refreshed every 2 hours at runtime.

**Config structure:** `config.py` holds all device IPs, MQTT/InfluxDB endpoints, device IDs, and polling intervals. `secret.py` holds all API keys and credentials (not in git).

**Grafana:**
- Grafana instance: `http://192.168.1.50:3000/` (configured in `config.py` as `grafanaConfig`)
- API token for reading dashboard variables: `grafanaApiKey` in `secret.py`
- Service account token for dashboard management: `grafanaServiceAccountToken` in `secret.py`
- `spec/grafana/` contains design specs (`.md`) and exported dashboard JSON (`.json`) for the "Prdikov" dashboard (UID `q50mEhf7k`)
- `grafana_setter.py` reads dashboard template variables and publishes them to MQTT

**Grafana workflow:** After deploying dashboard changes via API, always fetch the live JSON back and update `spec/grafana/prdikov.json` so the local copy stays in sync. Start from `prdikov.json` when making further changes — never build from scratch. **Always update the local design docs** (`spec/grafana/grafana-spec.md`, relevant `panel-*.jsx` files) to reflect any changes made to the dashboard.

### Prdikov Dashboard Panel Map (UID `q50mEhf7k`)

Dashboard: 24-column grid, 10s refresh, InfluxDB datasource (`ceyru5v6xg3r4b`).
Two-column layout: col 1 = 14 units, col 2 = 10 units. Design: `spec/grafana/design.html`.

| ID | Title | Type | GridPos (x,y,w,h) | Notes |
|----|-------|------|--------------------|-------|
| 70 | Outdoor | `dynamictext` (canvas) | 0,0,14,7 | Weather widget with sparkline |
| 67 | Indoor | `dynamictext` | 14,0,10,8 | 5 rooms + CO2 stat-bar |
| 80 | Energy Topology | `dynamictext` (SVG) | 0,7,14,8 | Solar/Grid → Inverter → Battery/House/Wallbox |
| 81 | Energy Chart + Stats | `dynamictext` (SVG) | 0,15,14,11 | Chart (Solar/House/Battery/Bojlery + OTE bars) + Energy Stats (Today/Month, Self-suff, Virt.batt) |
| 83 | Heat Tiles + TC + Stats | `dynamictext` | 14,8,10,10 | Krb + COP + Heat Pump tiles + TC chart + stat-bar |
| 86 | Vehicles | `dynamictext` | 14,18,10,10 | Enyaq + ID.3 SoC bars + per-car plug status pills (Connected/Charging/Disconnected) + GPS address |

Old panel designs archived in `spec/grafana/old/`.

### Grafana Design Docs

All panel documentation is consolidated in `spec/grafana/grafana-spec.md`, which covers:
- Dashboard architecture and grid layout
- Complete color scheme reference
- Flux query patterns and InfluxDB field reference
- Per-panel specs (queries, templates, color logic, CSS classes)
- Grafana compatibility notes

Old panel JSX visualizations archived in `spec/grafana/old/panel-*.jsx`.
Dashboard JSON is generated by `spec/grafana/build_dashboard.py` → `spec/grafana/prdikov.json`.
Visual reference: `spec/grafana/design.html` (serve with `python3 -m http.server`). Previous iteration archived as `redesign-v5.html`.
