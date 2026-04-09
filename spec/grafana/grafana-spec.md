# Prdikov Dashboard — Complete Panel Specification

Dashboard UID: `q50mEhf7k` | Datasource: InfluxDB (`ceyru5v6xg3r4b`) | Refresh: 10s | 24-column grid

---

## Table of Contents

1. [Dashboard Architecture](#dashboard-architecture)
2. [Color Scheme](#color-scheme)
3. [Query Patterns](#query-patterns)
4. [Panel 70 — Weather Widget](#panel-70--weather-widget)
5. [Panel 67 — Indoor / Rooms](#panel-67--indoor--rooms)
6. [Panel 68 — Power Flow v6](#panel-68--power-flow-v6)
7. [Panel 69 — OTE Electricity Price](#panel-69--ote-electricity-price)
8. [Panel 61 — Cars (Library Panel)](#panel-61--cars-library-panel)
9. [Panel 47 — TC-TEMP](#panel-47--tc-temp)
10. [Panel 2 — Power](#panel-2--power)
11. [Panel 43 — Power vs Forecast (Line)](#panel-43--power-vs-forecast-line)
12. [Panel 39 — Power vs Forecast (Bar)](#panel-39--power-vs-forecast-bar)
13. [Panel 50 — FVE Phases](#panel-50--fve-phases)
14. [Panel 24 — FVE Battery Life](#panel-24--fve-battery-life)
15. [Panel 20 — Solar Radiation](#panel-20--solar-radiation)
16. [Panel 57 — Heating State Timeline](#panel-57--heating-state-timeline)
17. [Panel 36 — Diagnostic Message](#panel-36--diagnostic-message)
18. [Panel 49 — COP Timewindow](#panel-49--cop-timewindow)
19. [Panel 10 — Outdoor Temperature](#panel-10--outdoor-temperature)
20. [Panel 66 — Rain Sparkline](#panel-66--rain-sparkline)
21. [InfluxDB Field Reference](#influxdb-field-reference)
22. [Grafana Compatibility Notes](#grafana-compatibility-notes)

---

## Dashboard Architecture

### Overview

Home automation dashboard built with Grafana + InfluxDB (Flux queries) + Business Text plugin (`marcusolsson-dynamictext-panel`). All custom panels use Handlebars templates with inline CSS. Canvas-based panels (70, 68) use `afterRender` JavaScript for animated visualizations.

Grafana config requires `disable_sanitize_html = true` in grafana.ini under `[panels]`.

### Grid Layout

```
Row 0-6:   [70 Weather+Clock (0,0,14,7)]  [67 Indoor/Rooms (14,0,10,7)]
Row 7-12:  [68 Power Flow (0,7,10,12)]  [47 TC-TEMP (10,7,7,6)]  [61 Cars (17,7,7,6)]
Row 13-18: [68 cont'd]  [2 Power (10,13,10,6)]  [69 OTE (20,13,4,6)]
Row 19-27: [43 Forecast Line (0,19,6,9)]  [39 Forecast Bar (6,19,10,9)]  [50 FVE Phases (17,19,7,7)]
           [24 Battery Life (17,26,2,6)]  [20 Solar Rad (19,26,2,6)]
Row 28+:   [57 Heating Timeline (0,28,13,11)]  [36 Diagnostic (13,32,8,4)]
           [49 COP (17,36,2,7)]  [10 Temp (0,39,4,6)]  [66 Rain Sparkline (0,45,4,2)]
```

### Panel Map

| ID | Title | Type | Grid (x,y,w,h) | JSX File |
|----|-------|------|-----------------|----------|
| 70 | Weather Widget | `dynamictext` (canvas) | 0,0,14,7 | `panel-70-weather.jsx` |
| 67 | Indoor / Rooms | `dynamictext` | 14,0,10,7 | `panel-67-indoor.jsx` |
| 68 | Power Flow v6 | `dynamictext` (canvas) | 0,7,10,12 | `panel-68-power-flow.jsx` |
| 47 | TC - TEMP | `timeseries` | 10,7,7,6 | `panel-47-tc-temp.jsx` |
| 61 | Cars | `library-panel-ref` | 17,7,7,6 | `panel-61-cars.jsx` |
| 2 | Power | `timeseries` | 10,13,10,6 | `panel-2-power.jsx` |
| 69 | OTE Price | `dynamictext` | 20,13,4,6 | `panel-69-ote.jsx` |
| 43 | Power vs Forecast | `timeseries` | 0,19,6,9 | `panel-43-forecast-line.jsx` |
| 39 | Power vs Forecast | `barchart` | 6,19,10,9 | `panel-39-forecast-bar.jsx` |
| 50 | FVE phases | `bargauge` | 17,19,7,7 | `panel-50-fve-phases.jsx` |
| 24 | FVE Battery life | `stat` | 17,26,2,6 | `panel-24-battery-life.jsx` |
| 20 | Solar Radiation | `stat` | 19,26,2,6 | `panel-20-solar-radiation.jsx` |
| 57 | Heating Timeline | `state-timeline` | 0,28,13,11 | `panel-57-heating-timeline.jsx` |
| 36 | Diagnostic message | `stat` | 13,32,8,4 | `panel-36-diagnostic.jsx` |
| 49 | COP timewindow | `stat` | 17,36,2,7 | `panel-49-cop.jsx` |
| 10 | Temp | `stat` | 0,39,4,6 | `panel-10-temp.jsx` |
| 66 | Rain Sparkline | `timeseries` | 0,45,4,2 | `panel-66-rain-sparkline.jsx` |

### Template Variables

Displayed in the dashboard header bar as dropdowns:

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `Termostat1NP` | 21 | 17,20,21,22,23,24,25,26 | Ground floor thermostat setpoint (°C) |
| `InverterDepthOfDischarge` | 70 | 10–90 (step 10) | Battery depth of discharge % — used in panel 68 for battery time remaining |
| `InverterStopChargingAt` | 90 | 10–100 (step 10) | Battery SoC % at which to stop grid charging |
| `WallboxAmp` | 16 | 6–16 | Maximum wallbox charging current (A) |
| `WallboxStartSOC` | 60 | 10–99 (step 10) | Battery SoC % threshold to allow car charging |
| `WallboxStopAtSOCDiff` | 10 | 1,2,3,4,5,10 | SoC hysteresis band for wallbox start/stop |
| `WallboxReserveAmp` | -1 | -5 to +5 | Reserved amps offset for wallbox (negative = more aggressive) |
| `WallboxMode` | Auto | Auto,Start,Stop,Disable | Wallbox operating mode |

These variables are read by `grafana_setter.py` and published to MQTT, where services like `wallbox.py` and `inverter_setter.py` consume them.

---

## Color Scheme

### Data Colors

| Data | Color | Hex | Used In |
|------|-------|-----|---------|
| Temperature (outdoor) | Yellow | `#f2cc0c` / `#FADE2A` | Panel 70 |
| Temp Hi (forecast) | Orange | `#FF9830` | Panel 70 |
| Temp Lo (forecast) | Blue | `#5794F2` | Panel 70 |
| Humidity | Blue | `#5794F2` | Panels 67, 70 |
| Rain | Purple | `#B877D9` | Panels 66, 70 |
| Wind sustained | White | `#d8d9da` | Panel 70 |
| Wind 30m max | Orange | `#FF9830` | Panel 70 |
| Wind forecast line | Blue | `#5794F2` | Panel 70 sparkline |

### Indoor Temperature Color Gradient

Applied to each room temperature value in panel 67:

| Range | Color | Hex |
|-------|-------|-----|
| > 26°C | Red | `#f2495c` |
| > 25°C | Warm red | `#dd5d5e` |
| > 24°C | Brown-orange | `#b38463` |
| > 23°C | Yellow-green | `#88ab67` |
| > 20°C | Green | `#73bf69` |
| > 16°C | Muted green | `#80b368` |
| > 12°C | Olive | `#999c65` |
| > 8°C | Brown-orange | `#b38463` |
| > 4°C | Red-orange | `#cc6c60` |
| ≤ 4°C | Red | `#f2495c` |

### Energy Colors

| Data | Condition | Color | Hex |
|------|-----------|-------|-----|
| Solar production | < 2 kW | Light green | `#a6e09e` |
| Solar production | 1–2 kW | Green | `#73bf69` |
| Solar production | 2–4 kW | Dark green | `#4a9e3f` |
| Solar production | 4–6 kW | Light blue | `#73C0F5` |
| Solar production | 6–8 kW | Blue | `#5794F2` |
| Solar production | > 8 kW | Dark blue | `#3d6fd4` |
| House consumption | < 2 kW | Green | `#73bf69` |
| House consumption | 2–4 kW | Yellow | `#FADE2A` |
| House consumption | 4–6 kW | Orange | `#FF9830` |
| House consumption | > 6 kW | Red | `#f2495c` |
| Battery SoC | > 90% | Blue | `#5794F2` |
| Battery SoC | 30–90% | Green | `#73bf69` |
| Battery SoC | 20–30% | Orange | `#FF9830` |
| Battery SoC | 10–20% | Orange-red | `#FF6B3D` |
| Battery SoC | < 10% | Red | `#f2495c` |
| Grid import | mild | Yellow | `#FADE2A` |
| Grid import | moderate (3–7 kW) | Orange | `#FF9830` |
| Grid import | heavy (> 7 kW) | Red | `#f2495c` |
| Grid export | mild | Yellow | `#FADE2A` |
| Grid export | moderate (3–7 kW) | Light blue | `#73C0F5` |
| Grid export | heavy (> 7 kW) | Blue | `#5794F2` |
| Wallbox | Active | Orange | `#FF9830` |
| Wallbox | Disconnected | Gray | `#4a4a4a` |
| Battery state (v6 canvas) | Charging | Green | `#44ee44` |
| Battery state (v6 canvas) | Discharging | Red | `#ff4444` |
| Battery state (v6 canvas) | Idle | Gray | `#666666` |
| Car SoC | > 90% | Purple | `#B877D9` |
| Car SoC | > 20% | Green | `#73bf69` |
| Car SoC | ≤ 20% | Red | `#f2495c` |

### UI Colors

| Element | Hex | Usage |
|---------|-----|-------|
| Panel background | `#181b1f` | Default |
| Card background | `#1e2228` | Indoor rows, OTE card |
| Cell background (v6) | `#0a0a0a` | Power flow grid cells |
| Stats bar | `#111217` | Weather stats |
| Labels / units | `#8e8e8e` | All panels |
| Default text | `#d8d9da` | Values |
| Dividers | `#2c3035` | Vertical separators |
| Krb ON | `#73bf69` | Fireplace active |
| Krb OFF | `#f2495c` | Fireplace inactive |
| CO2 < 800 | `#73bf69` | Good air quality |
| CO2 800–1000 | `#FF9830` | Moderate |
| CO2 > 1000 | `#f2495c` | Poor air quality |

---

## Query Patterns

All Business Text panels use the same Flux pattern:

1. **findRecord** to extract each field as a scalar value
2. **`if exists ... then ... else 0.0`** for null safety
3. **`float(v:)`** cast to avoid type mismatch errors
4. **`math.round()`** for clean display values (1 decimal: `* 10.0 / 10.0`, 2 decimal: `* 100.0 / 100.0`)
5. **`array.from(rows: [...])`** to build final single-row output
6. **Safe union+default pattern** for optional fields: union a default row `{_time: 2000-01-01, _value: 0.0}` with real data, sort by time, take last — guarantees a value exists even if no data

### Business Text Panel Settings

- Render template: **Every row**
- Primary Content Language: **Handlebars**
- Wrap automatically in paragraphs: **Disabled**
- Handlebars helpers: `gt` (built-in), `eq` (built-in); custom: `lt`, `abs`, `gte` (registered in helpers/afterRender JS)

---

## Panel 70 — Weather Widget

**Type:** Business Text (canvas-based via afterRender JS)
**Grid:** (0,0,14,7) — top-left, 14 columns wide

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [☀️/🌧️]  18.4°C    Hi 23°    |                    14:32:05     │
│                    Lo 14°    |                    07.04.26      │
├─────────────────────────────────────────────────────────────────┤
│ [SVG Sparkline: temp line (yellow), rain bars (purple),         │
│  wind line (blue), now marker (yellow dot + dashed line),       │
│  hi/lo labels (orange/blue)]                                    │
├─────────────────────────────────────────────────────────────────┤
│ Humidity  │  Wind    km/h  30m   km/h  │  Rain                  │
│ 72%       │  12 / 18      15 / 22      │  0.0 mm/h  2.1 fc  4.2 tot │
└─────────────────────────────────────────────────────────────────┘
```

### Flux Query

```flux
import "array"
import "math"
import "strings"
import "date"
import "timezone"

option location = timezone.location(name: "Europe/Prague")

// Current weather values (findRecord pattern)
temp, maxtemp, mintemp, humidity, precip, precipRate, windSpeed,
windGust, precipTotal, wind30m, windGust30m  — each from respective measurements

// Hourly forecast data (encoded as "H:val,H:val,..." strings)
hourly_data   — TempForecast.temperature (today, sorted by hour)
rain_data     — RainForecast.precipitation (today)
wind_data     — WindForecast.wind_speed (today)

// Output: single row
array.from(rows: [{
  temp, hi, lo, humidity, rain_fc, rain_rate, rain_total,
  wind, gust, wind_30m, gust_30m,
  hourly (string), rain_hourly (string), wind_hourly (string)
}])
```

### Rounding

| Field | Precision | Method |
|-------|-----------|--------|
| temp, rain_fc, rain_rate, rain_total | 1 decimal | `* 10.0 / 10.0` |
| hi, lo, humidity, wind, gust, wind_30m, gust_30m | integer | `math.round()` |

### Content Template (Handlebars + HTML)

Data attributes are set on the root div (`data-temp`, `data-hourly`, etc.) and read by afterRender JS.

- **Hero row:** Weather icon (dynamic SVG: sun+cloud for day, cloud for night/rain, rain drops for >1mm/h), big temperature, hi/lo, live clock (updated every 1s via setInterval)
- **Sparkline:** SVG rendered in afterRender JS using Catmull-Rom spline interpolation for smooth curves
  - Yellow temperature line (#f2cc0c) with gradient fill
  - Purple rain bars (#B877D9) with opacity proportional to amount
  - Blue wind line (#5794F2, opacity 0.6)
  - Now marker: yellow dot + dashed vertical line
  - Hi/Lo peak labels (orange/blue)
  - Hour labels every 3h
- **Stats bar:** 3-section flex layout with separators
  - Humidity (flex: 0.67): blue value
  - Wind: current + 30m max (white / orange), slash notation with gusts
  - Rain: rate (mm/h) + forecast (fc) + total (tot), all purple

### Color Logic

| Element | Condition | Color |
|---------|-----------|-------|
| Temperature text | ≤ 0°C | `#4fc3f7` (cold blue) |
| Temperature text | ≥ 30°C | `#f2495c` (red) |
| Temperature text | default | `#f2cc0c` (yellow) |
| Weather icon | rain rate > 1 | Cloud with rain drops |
| Weather icon | rain rate > 0 | Double cloud (overcast) |
| Weather icon | day (7-19h) | Sun + cloud |
| Weather icon | night | Double cloud |

### CSS Classes

| Class | Size | Purpose |
|-------|------|---------|
| `.ww-temp` | 4.7vw | Big temperature |
| `.ww-deg` | 2.1vw | °C symbol |
| `.ww-hi` / `.ww-lo` | 1.4vw | Forecast hi/lo |
| `.ww-clock-time` | 2.75vw | Clock HH:MM:SS |
| `.ww-clock-date` | 1.35vw | Date DD.MM.YY |
| `.ww-val` | 3.63vw | Stat values |
| `.ww-label` | 1.16vw | Stat labels |
| `.ww-sub` | 1.82vw | Gust values (gray) |
| `.ww-sub-orange` | 1.82vw | 30m gust values |
| `.ww-rain-val` | 2.64vw | Rain values |

---

## Panel 67 — Indoor / Rooms

**Type:** Business Text (Handlebars)
**Grid:** (14,0,10,7) — top-right

### Layout

```
┌─────────────────────────────┬───┬──────────────┐
│ Obyvacka  22.1° ▸22.0° 48% ▲│   │ Krb     ON   │
│ Pracovna  21.5° ▸21.0° 52% ▲│   │ Krb T   65°  │
│ Julinka   20.8° ▸20.0°     ▲│   │ COP 24h 3.45 │
│ Kubo      21.2° ▸21.0°     ▲│   │ CO2     742  │
│ Spalna    19.5° ▸19.0°      │   │   ppm        │
└─────────────────────────────┴───┴──────────────┘
```

### Flux Query

```flux
import "array"
import "math"

// Room temperatures
obyvacka_temp   — weather.temperature_upstairs_in
pracovna_temp   — rehau.Pracovna
julinka_temp    — netatmo.julinka
kubo_temp       — netatmo.kubo
spalna_temp     — netatmo.spalna

// Room humidity (Obyvacka + Pracovna only)
obyvacka_hum    — weather.humidity_upstairs_in
pracovna_hum    — rehau_hum.Pracovna

// Setpoints
obyvacka_set    — rehau_set.Obyvacka
pracovna_set    — rehau_set.Pracovna
julinka_set     — temp_target.julinka
kubo_set        — temp_target.kubo
spalna_set      — temp_target.spalna

// Heating active indicators
oby_heat        — rehau_output.Obyvacka-1
pra_heat        — rehau_output.Pracovna
jul_heat        — on.julinka
kub_heat        — on.kubo
spa_heat        — on.spalna

// Heating system status
co2             — weather.moes_co2
krb_power       — krb.apower
krb_temp        — krb.tC
cop             — Estia.cop_24h (range: -24h)

// Output fields with null safety
array.from(rows: [{
  oby_t, oby_h, oby_set, pra_t, pra_h, pra_set,
  jul_t, kub_t, spa_t, jul_set, kub_set, spa_set,
  co2, krb_w, krb_t, cop,
  oby_on, pra_on, jul_on, kub_on, spa_on
}])
```

### Template Logic

**Left column — Rooms:**
Each room is a `.indoor-room` card containing:
- Room name (`.indoor-name`, 0.8vw)
- Temperature (`.indoor-temp`, 1.8vw) — color from gradient table
- Target (`.indoor-target`, 1.1vw) with `▸` arrow prefix
- Humidity (`.indoor-hum`, 1.4vw, blue) — Obyvacka & Pracovna only
- Heating indicator `▲` (`.indoor-heat-arrow`, orange #FF9830) — shown when `*_on > 0`

**Right column — Status:**
- **Krb**: ON/OFF based on `krb_w > 20` — green/red
- **Krb T**: fireplace temperature with gradient coloring (>70 red, 60-70 gradient, 15-60 green, <15 cold gradient)
- **COP 24h**: coefficient of performance, always green #73bf69
- **CO2**: large card (`.indoor-heat-row-lg`), colored by threshold (green <800, orange 800-1000, red >1000), shows "ppm" unit

### Krb Temperature Color Logic

| Range | Color | Hex |
|-------|-------|-----|
| > 70°C | Red | `#f2495c` |
| > 65°C | Red-brown | `#c87060` |
| > 60°C | Olive | `#9d9865` |
| > 15°C | Green | `#73bf69` |
| > 10°C | Olive | `#9d9865` |
| > 5°C | Red-brown | `#c87060` |
| ≤ 5°C | Red | `#f2495c` |

---

## Panel 68 — Power Flow v6

**Type:** Business Text (canvas-based via afterRender JS)
**Grid:** (0,7,10,12) — large left panel

### Layout

3×3 CSS grid with canvas-rendered animated icons:

```
┌─────────────┬─────────────┬─────────────┐
│  ☀️ Solar    │ 🔄 Self-Suf  │  🏠 House    │
│  3.42 kW    │    67%       │  2.18 kW    │
├─────────────┼─────────────┼─────────────┤
│  🔋 Battery  │  ⚡ Grid     │  🚗 Wallbox  │
│  72% +0.85  │  +1.24 kW   │  6.5 kW     │
│  ~2h 15m    │  EXPORT      │             │
├─────────────┼─────────────┼─────────────┤
│  📊 TODAY    │ 🔋 V.Battery │  📅 MONTH    │
│  C 15.2 kWh │    87%       │  C 487 kWh  │
│  P 18.7 kWh │ SOLD/BOUGHT  │  P 523 kWh  │
└─────────────┴─────────────┴─────────────┘
```

### Flux Query

```flux
import "math"
import "array"
import "date"

// Live readings (FVE measurement)
prod_raw     — FVE.power (string="all")
cons_raw     — FVE.consumption
bat_raw      — FVE.battery_load
soc_raw      — FVE.soc
meter_rec    — FVE.meter_power (safe union+default pattern)
charge_rec   — Car.charging_wallbox_power (safe pattern)
conn_rec     — Car.car_connected (safe pattern)

// Daily stats
d_cons_raw   — FVE.consumption_day
d_gen_raw    — FVE.generation_day

// Monthly stats (sum of daily max for current month)
m_cons_raw   — FVE.consumption_day |> aggregateWindow(1d, max) |> sum()
m_gen_raw    — FVE.generation_day  |> aggregateWindow(1d, max) |> sum()

// Virtual Battery (CEZ)
vb_charge_raw — cez.virtual_battery
vb_prod_raw   — cez.aggregated_production
vb_cons_raw   — cez.aggregated_consumption

// Computed values
// IMPORTANT: House node shows consumption MINUS wallbox power
cons = cons_total - charge  (so House = pure house load, Wallbox is separate)
self_suf = d_gen / d_cons * 100  (can exceed 100% on sunny days)
vb_pct = vb_prod / vb_cons * 100

// Battery time remaining (discharge)
dod = ${InverterDepthOfDischarge}  // template variable
usable_kwh = (soc - (100 - dod)) / 100 * 20.0  // 20 kWh battery
bat_hours = usable_kwh / discharge_kw

// Battery time to full (charge, capped at SoCStop)
soc_stop = ${InverterStopChargingAt}  // template variable
remaining_kwh = (soc_stop - soc) / 100 * 20.0
bat_chg_hours = remaining_kwh / charge_kw

// Output (all values converted to kW with 2 decimal places)
array.from(rows: [{
  prod, cons, soc, bat, meter, charge_w, car_conn,
  d_cons, d_gen, m_cons, m_gen, self_suf,
  vb_charge, vb_prod, vb_cons, vb_pct,
  bat_hrs, bat_mins, bat_chg_hrs, bat_chg_mins
}])
```

### Canvas Rendering (afterRender JS)

Each cell has a `<canvas>` element. The afterRender JS uses `requestAnimationFrame` with ~250ms frame skipping (~4fps) and **auto-stops after 3 seconds**. Since Grafana re-renders the panel every 10s (data refresh), `afterRender` re-triggers and animates for another 3s burst. Between bursts, zero CPU/memory cost.

**Performance optimizations (v6.1):**
- No `shadowBlur` anywhere — glow effects use wider, lower-opacity duplicate strokes (10x cheaper on Safari)
- Gradients (`createRadialGradient`, `createLinearGradient`) are created once per data refresh and cached, not per frame (fixes Chrome memory pressure causing tab reloads)
- No CSS infinite `@keyframes` — shimmer/glow on energy bars are static gradient overlays
- Grid direction uses a static colored wire overlay + bouncing arrow (no `lineDashOffset` animation, which is expensive in Safari)
- `requestAnimationFrame` instead of `setInterval` — respects tab visibility, pauses when backgrounded

**Solar cell:** Radial glow (cached gradients), sun icon with animated rays (length proportional to power), solar panel graphic, kW value below. Color shifts green→blue with increasing power.

**House cell:** House outline with animated glowing windows (number lit ∝ consumption). Glow via double-filled rects (no shadowBlur). Hue shifts green→yellow→red with load. Value below.

**Battery cell:** Horizontal battery shape with fill bar (width = SoC%, cached gradient using 5-tier SoC colors), ±kW value. SoC% text is always white `#fff` for contrast against the colored fill. Time remaining shown below when charging/discharging. State color: green `#44ee44` when charging (bat < -0.25 kW), red `#ff4444` when discharging (bat > 0.25 kW), gray `#666` when idle. Border and terminal colored by state; pulsing border glow via wider stroke (no shadowBlur). No bolt icon — removed to keep SoC% readable.

**Grid cell:** Transmission line graphic with static colored overlay (opacity ∝ power magnitude). Arrow bounces left/right. Value + IMPORT/EXPORT/BALANCED badge.

**Wallbox cell:** Charger station with cable to car graphic. Charge level bars inside car (signal-bar style). Pulsing when actively charging. Greyed out when disconnected (`.pf6-off`).

**Self-Sufficiency cell:** 270° arc gauge, percentage in center. Glow via wider lower-opacity stroke (no shadowBlur). Color: ≥80% green, ≥50% orange, <50% red.

**Virtual Battery cell:** Smaller arc gauge + SOLD/BOUGHT footer with values. Same glow technique.

**Today/Month cells:** Dual horizontal bar gauges with static shimmer overlay. Consumed (red gradient) and Produced (green gradient), proportional to max of both.

### Grid Badge Colors

| State | Background | Text | Threshold |
|-------|-----------|------|-----------|
| IMPORT | `#3a1a1a` | `#ff5050` | meter < -0.25 kW |
| EXPORT | `#1c3a20` | `#50ff78` | meter > +0.25 kW |
| BALANCED | `#1a2a3a` | `#50a0ff` | \|meter\| ≤ 0.25 kW |

---

## Panel 69 — OTE Electricity Price

**Type:** Business Text (Handlebars)
**Grid:** (20,13,4,6) — small right panel

### Layout

```
┌──────────────────────┐
│ OTE Today   CZK/kWh  │
│                       │
│       2.45            │
│    now · 14:00        │
│                       │
│ [green───●───red bar] │
│                       │
│ MIN         MAX       │
│ 1.23       4.56       │
│ @3:00      @18:00     │
└──────────────────────┘
```

### Flux Query

```flux
import "math"
import "experimental"
import "array"
import "date"
import "timezone"

option location = timezone.location(name: "Europe/Prague")

// OTE hourly prices for today
ote_raw — OTE.price_czk_kwh (type="hourly"), range: today → today+25h

// Current hour price (Prague time)
// Data stored at end-of-hour: 8-9am price at 09:00 timestamp
now_hour = date.hour(t: now(), location: _loc)
ote_cur — filter by hour == now_hour + 1

// Min/Max with safe defaults (999 / -999)
ote_min — min of ote_raw
ote_max — max of ote_raw
// Hours adjusted: subtract 1 from timestamp hour for display

// Dot position: (cur - min) / (max - min) * 100, clamped 2-98%

// Output (all as strings for display)
array.from(rows: [{
  cur_price, cur_hour, min_price, min_hour,
  max_price, max_hour, dot_pct
}])
```

### Template

- Card background: `#1e2128`
- Header: label "OTE Today" + unit "CZK/kWh" in gray
- Hero: current price (32px bold), sub-label "now · HH:00"
- Range bar: `linear-gradient(to right, #73BF69, #FF9830, #F2495C)`, 5px height, 3px border-radius
- White dot (11px circle) positioned at `dot_pct%`
- MIN (green #73BF69) and MAX (red #F2495C) with hour labels

### CSS Classes

| Class | Purpose |
|-------|---------|
| `.ov-wrap` | Flex column container |
| `.ov-card` | Card with #1e2128 bg |
| `.ov-hero-val` | Big price (32px) |
| `.ov-bar` | Gradient price range bar |
| `.ov-dot` | White position indicator |
| `.ov-mm-val` | Min/max values (18px) |

---

## Panel 61 — Cars (Library Panel)

**Type:** Business Text (Handlebars), Library Panel UID: `ffhemurxfumf4a`
**Grid:** (17,7,7,6) — rendered per row (2 rows: Enyaq, ID.3)

### Layout

```
┌──────────────────────────────────────────────┐
│ Enyaq  [████████████████░░░░░░░░] 78%        │
│        Range 285 km   Max 365 km             │
├──────────────────────────────────────────────┤
│ ID.3   [█████████░░░░░░░░░░░░░░░] 45%        │
│        Range 142 km   Max 315 km  Left 47 min│
└──────────────────────────────────────────────┘
```

### Flux Query

```flux
import "math"
import "array"

// Per-car: soc, range, time_left
// Union + pivot pattern to build 2 rows

// Shared wallbox power (safe union+default)
// Default time_left rows (0.0)

// Computed: max_range = range / soc * 100

// Output: 2 rows with car, soc, range, max_range, charge_w, time_left
```

### SoC Bar Design

The gradient is on `.car-bar-track`: `linear-gradient(90deg, #f2495c 0%, #73bf69 20%, #73bf69 90%, #B877D9 100%)`.

A transparent spacer (width = SoC%) reveals the gradient, then:
- **Not charging:** dark cover (`#1e2228`) hides the rest
- **Charging (time_left > 0):** pulsing green animation (`#2a3a2a` ↔ `#3d5c3d`, 1.5s cycle)

### SoC Color Logic

| SoC Range | Color | Hex |
|-----------|-------|-----|
| > 90% | Blue | `#5794F2` |
| 30–90% | Green | `#73BF69` |
| 20–30% | Orange | `#FF9830` |
| 10–20% | Orange-red | `#FF6B3D` |
| < 10% | Red | `#F2495C` |

### Stats Row

- **Range** and **Max** always shown
- **Left** (minutes, orange `#FF9830`) shown only when `time_left > 0`
- `charge_w` is in query output but not displayed (used by power flow panel)

---

## Panel 47 — TC-TEMP

**Type:** Native Time Series
**Grid:** (10,7,7,6) | **Title:** "TC - TEMP"

### Queries

**Query 0:** Heat pump target temperature
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "target_temp")
  |> aggregateWindow(every: v.windowPeriod, fn: last)
```

**Query 1:** Fireplace (becka) temperature
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "becka" and r._field == "tC")
  |> aggregateWindow(every: v.windowPeriod, fn: last)
```

### Visual Config

- Line width: **5**, Fill opacity: **0**
- Color mode: palette-classic

### Overrides

| Series | Display Name | Color |
|--------|-------------|-------|
| `in_temp` | — | dark-blue |
| `out_temp` | — | dark-red |
| `target_temp` | — | dark-green |
| `becka tC` | — | orange |

---

## Panel 2 — Power

**Type:** Native Time Series
**Grid:** (10,13,10,6) | **Title:** "Power"

### Queries

**Query 0:** Consumption + Bojlery (hot water heaters, tagged with `pretoky="pretoky"`)
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and
    r._field == "consumption" or r._field == "bojlery")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

**Query 1:** Battery load
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "battery_load")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

**Query 2:** Solar production (all strings except individual string 1 and 2)
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and
    r._field == "power" and r.string != "1" and r.string != "2")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

### Visual Config

- Line width: **1**, Fill opacity: **20**

### Overrides

| Series | Display Name | Color |
|--------|-------------|-------|
| `power {string="all"}` | power | light-blue |
| `battery_load` | — | light-yellow |
| `consumption` | — | green |
| `bojlery {pretoky="pretoky"}` | bojlery | orange |

---

## Panel 43 — Power vs Forecast (Line)

**Type:** Native Time Series
**Grid:** (0,19,6,9) | **Title:** "Power vs Forecast"

### Queries

**Query 0:** Solar forecast bands (10th, 50th, 90th percentile cumulative)
```flux
from(bucket: "default")
  |> range(start: 5h after day start, stop: 18h after day start)
  |> filter(fn: (r) => r._measurement == "SolarForecast" and
    (r._field == "30m_10p_cummulative" or r._field == "30m_50p_cummulative"
     or r._field == "30m_90p_cummulative"))
  |> aggregateWindow(every: 30m, fn: last)
```

**Query 1:** Actual generation
```flux
from(bucket: "default")
  |> range(start: 5h, stop: 18h)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "generation_day")
  |> aggregateWindow(every: 30m, fn: mean)
```

### Visual Config

- Line width: **3**, Fill opacity: **50**

### Overrides

| Series | Style | Color | Notes |
|--------|-------|-------|-------|
| 90p cumulative | lineWidth=0, fillBelowTo=10p | light-green | Shaded band |
| 50p cumulative | line, fillOpacity=0 | green | Center forecast line |
| 10p cumulative | lineWidth=0, fillOpacity=0 | — | Bottom of band |
| Actual generation | bars, lineWidth=3, fillOpacity=50 | default | Bar overlay |

---

## Panel 39 — Power vs Forecast (Bar)

**Type:** Native Bar Chart
**Grid:** (6,19,10,9) | **Title:** "Power vs Forecast"

### Queries

**Query 0:** Solar forecast 50th percentile (30m intervals, 5h-18h)
**Query 1:** Actual generation (same range)

### Visual Config

- Fill opacity: **80**

### Overrides

| Series | Display Name | Color |
|--------|-------------|-------|
| SolarForecast 30m_50p_cummulative | forecast | green |
| FVE generation_day | generation | blue |

---

## Panel 50 — FVE Phases

**Type:** Native Bar Gauge
**Grid:** (17,19,7,7) | **Title:** "FVE phases"

### Query

```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "curr")
  |> aggregateWindow(every: v.windowPeriod, fn: last)
```

### Visual Config

- Color mode: **continuous-BlYlRd** (blue → yellow → red)
- Threshold: yellow at 0

### Overrides (Display Names)

| Series | Display Name |
|--------|-------------|
| `curr 1` | Phase 1 (traktor, KL, pracka) |
| `curr 2` | Phase 2 (mycka) |
| `curr 3` | Phase 3 (AC, trouba) |

---

## Panel 24 — FVE Battery Life

**Type:** Native Stat
**Grid:** (17,26,2,6) | **Title:** "FVE Battery life"

### Queries

**Query 0:** Battery cycles (charged kWh / 14.8 kWh capacity)
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and
    r._field == "battery_charged" and r.sum == "total")
  |> map(fn: (r) => ({battery_charged: (r._value / 14.8)}))
```

**Query 1:** State of Health (SOH)
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "soh")
```

### Overrides

| Series | Display Name | Unit |
|--------|-------------|------|
| FVE soh | SOH | percent |
| battery_charged | Cycles | — |

- Color: fixed text (white)
- Threshold: green at 0

---

## Panel 20 — Solar Radiation

**Type:** Native Stat
**Grid:** (19,26,2,6) | **Title:** "Solar Radiation"

### Query

```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "weather" and r._field == "solarRadiation")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

- Color mode: **continuous-BlYlRd**
- Unit: W/m² (implicit from data)

---

## Panel 57 — Heating State Timeline

**Type:** Native State Timeline
**Grid:** (0,28,13,11) | **Title:** "Panel Title" (untitled in practice)

### Queries

**Query 0:** Rehau floor heating output zones
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "rehau_output")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

**Query 1:** Netatmo heating on/off
```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "on")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

### Visual Config

- Line width: **4**, Fill opacity: **59**
- Color mode: **thresholds**

### Thresholds

| Value | Color | Meaning |
|-------|-------|---------|
| 0 | semi-dark-red | Off |
| 0.2 | super-light-green | Starting |
| 0.5 | light-green | Partial |
| 0.7 | semi-dark-green | Active |
| 0.9 | dark-green | Full |

---

## Panel 36 — Diagnostic Message

**Type:** Native Stat
**Grid:** (13,32,8,4) | **Title:** "Diagnostic message"

### Query

```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "diag")
  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)
```

- Color mode: **thresholds** (green at 0, red at 80)
- Shows the latest diagnostic string from the inverter

---

## Panel 49 — COP Timewindow

**Type:** Native Stat
**Grid:** (17,36,2,7) | **Title:** "COP timewindow"

### Query

Consumption-weighted COP over the dashboard time range:

```flux
import "date"

from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "Estia" and
    r._field == "cop_24h" or r._field == "consumption_24h")
  |> aggregateWindow(every: 1d, fn: last)
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> map(fn: (r) => ({
      _time: r._time,
      weighted_cop: r.cop_24h * r.consumption_24h,
      consumption_24h: r.consumption_24h
  }))
  |> reduce(
      fn: (r, accumulator) => ({
          consumption_24h: accumulator.consumption_24h + r.consumption_24h,
          weighted_cop: accumulator.weighted_cop + r.weighted_cop
      }),
      identity: {consumption_24h: 0.0, weighted_cop: 0.0}
  )
  |> map(fn: (r) => ({
      _time: r._time,
      cop: r.weighted_cop / r.consumption_24h
  }))
```

- Color mode: **continuous-RdYlGr** (red → yellow → green)
- This gives a consumption-weighted average COP, not just the latest 24h value

---

## Panel 10 — Outdoor Temperature

**Type:** Native Stat
**Grid:** (0,39,4,6) | **Title:** "Temp"

### Query

```flux
from(bucket: "default")
  |> filter(fn: (r) =>
    (r._measurement == "estia" and r._field == "outside_temp") or
    (r._measurement == "weather" and r._field == "temperature"))
  |> aggregateWindow(every: v.windowPeriod, fn: last)
  |> fill(usePrevious: true)
  |> elapsed(unit: v.windowPeriod)
  |> map(fn: (r) => ({
      r with _value: if r.elapsed <= 3 then r._value else NaN
  }))
  |> drop(columns: ["elapsed"])
```

- Color mode: **continuous-BlYlRd**
- Shows both weather station and estia outside temp
- Staleness check: values older than 3 periods are set to NaN (prevents showing stale data)

---

## Panel 66 — Rain Sparkline

**Type:** Native Time Series
**Grid:** (0,45,4,2) — tiny sparkline, no title

### Query

```flux
from(bucket: "default")
  |> filter(fn: (r) => r._measurement == "weather" and r._field == "precipRate")
  |> aggregateWindow(every: v.windowPeriod, fn: max)
```

### Visual Config

- Color: fixed purple `#B877D9`
- Line width: **1**, Fill opacity: **10**
- No title, no legend, hidden axes
- Transparent background

---

## InfluxDB Field Reference

### Weather (measurement: `weather`)

| Field | Description | Unit |
|-------|-------------|------|
| `temperature` | Outdoor temperature | °C |
| `humidity` | Outdoor humidity | % |
| `precipRate` | Current rain rate | mm/h |
| `precipTotal` | Accumulated rain total | mm |
| `windSpeed` | Sustained wind speed | km/h |
| `windGust` | Wind gust speed | km/h |
| `solarRadiation` | Solar radiation intensity | W/m² |
| `temperature_upstairs_in` | Obyvacka (living room) temperature | °C |
| `humidity_upstairs_in` | Obyvacka humidity | % |
| `moes_co2` | CO2 sensor reading | ppm |

### Weather Forecast (measurement: `weatherforecast`)

| Field | Description | Unit |
|-------|-------------|------|
| `maxtemp` | YR.no forecast daily high | °C |
| `mintemp` | YR.no forecast daily low | °C |
| `precip` | YR.no forecast precipitation | mm |

### Hourly Forecasts

| Measurement | Field | Description |
|-------------|-------|-------------|
| `TempForecast` | `temperature` | Hourly temperature forecast |
| `RainForecast` | `precipitation` | Hourly rain forecast |
| `WindForecast` | `wind_speed` | Hourly wind speed forecast |

### Indoor — Rehau Floor Heating

| Measurement | Field | Description |
|-------------|-------|-------------|
| `rehau` | `Pracovna` | Pracovna temperature (°C) |
| `rehau_hum` | `Pracovna` | Pracovna humidity (%) |
| `rehau_set` | `Obyvacka`, `Pracovna` | Target temperatures (°C) |
| `rehau_output` | `Obyvacka-1`, `Pracovna`, etc. | Floor heating valve output (0–1) |

### Indoor — Netatmo Thermostats

| Measurement | Field | Description |
|-------------|-------|-------------|
| `netatmo` | `julinka`, `kubo`, `spalna`, `hala` | Room temperatures (°C) |
| `temp_target` | `julinka`, `kubo`, `spalna`, `hala`, `kupelna`, `chodba`, `hostovska` | Thermostat target temps (°C) |
| `on` | `julinka`, `kubo`, `spalna` | Heating active (0/1) |

### Fireplace (measurement: `krb`)

| Field | Description | Unit |
|-------|-------------|------|
| `apower` | Fireplace power (ON if > 20W) | W |
| `tC` | Fireplace temperature | °C |

### Heat Pump (measurement: `Estia` / `estia`)

| Field | Description | Unit |
|-------|-------------|------|
| `cop_24h` | 24-hour COP | ratio |
| `consumption_24h` | 24-hour energy consumption | kWh |
| `target_temp` | Target water temperature | °C |
| `outside_temp` | Heat pump outside temperature sensor | °C |

### Fireplace sensor (measurement: `becka`)

| Field | Description | Unit |
|-------|-------------|------|
| `tC` | Water temperature from fireplace heat exchanger | °C |

### Cars (measurement: `Car`)

| Field | Description | Unit |
|-------|-------------|------|
| `battery_level_enyaq` | Enyaq SoC | % |
| `electric_range_enyaq` | Enyaq estimated range | km |
| `charging_time_left_enyaq` | Enyaq charge time remaining | min |
| `battery_level_vw` | ID.3 SoC | % |
| `electric_range_vw` | ID.3 estimated range | km |
| `charging_time_left_vw` | ID.3 charge time remaining | min |
| `charging_wallbox_power` | Wallbox charge power (shared) | W |
| `car_connected` | Car plugged in (1=yes, 0=no) | bool |

### Solar / FVE (measurement: `FVE`)

| Field | Tag | Description | Unit |
|-------|-----|-------------|------|
| `power` | `string="all"` | Current PV production | W |
| `consumption` | — | Current house consumption | W |
| `soc` | — | Battery state of charge | % |
| `battery_load` | — | Battery power (+ = discharge, - = charge) | W |
| `meter_power` | — | Grid meter (- = import, + = export) | W |
| `consumption_day` | — | Today's cumulative consumption | kWh |
| `generation_day` | — | Today's cumulative generation | kWh |
| `battery_charged` | `sum="total"` | Lifetime battery charged energy | kWh |
| `soh` | — | Battery state of health | % |
| `diag` | — | Diagnostic message string | text |
| `curr` | (tag: 1/2/3) | Phase current | A |
| `bojlery` | `pretoky="pretoky"` | Hot water heater overflow power | W |

### Solar Forecast (measurement: `SolarForecast`)

| Field | Description | Unit |
|-------|-------------|------|
| `30m_10p_cummulative` | 10th percentile cumulative forecast | kWh |
| `30m_50p_cummulative` | 50th percentile (median) forecast | kWh |
| `30m_90p_cummulative` | 90th percentile cumulative forecast | kWh |

### Electricity Price (measurement: `OTE`)

| Field | Tag | Description | Unit |
|-------|-----|-------------|------|
| `price_czk_kwh` | `type="hourly"` | Hourly electricity price | CZK/kWh |

**Note:** OTE timestamps are end-of-hour — the price for 8:00-9:00 is stored at 09:00. Display logic subtracts 1 from the hour.

### Virtual Battery — CEZ (measurement: `cez`)

| Field | Description | Unit |
|-------|-------------|------|
| `virtual_battery` | Current virtual battery charge | kWh |
| `aggregated_production` | Aggregated exported energy | kWh |
| `aggregated_consumption` | Aggregated imported energy | kWh |

### Monthly Stats Calculation

```flux
month_start = date.truncate(t: now(), unit: 1mo)
from(bucket: "default")
  |> range(start: month_start)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "consumption_day")
  |> aggregateWindow(every: 1d, fn: max)
  |> sum()
```

### Constants

- Max PV power: **9000 W** (used for bar gauge scaling)
- Battery capacity: **20 kWh** (used for time remaining calculation)
- Battery cell capacity: **14.8 kWh** (used for cycle count)
- Krb ON threshold: **> 20 W**

---

## Grafana Compatibility Notes

- `@keyframes` with `background-color` works in Business Text; `opacity` animation and `::after` pseudo-elements do **not**
- Real DOM elements must be used instead of CSS pseudo-elements for overlays
- Inline `style` attributes on Handlebars-generated elements work reliably
- `disable_sanitize_html = true` required in `grafana.ini` `[panels]` section
- Canvas rendering via `afterRender` JS uses `setInterval` at 250ms (~4fps), not `requestAnimationFrame` (Safari compatibility)
- `handlebars` variable is available in the **helpers** editor (Before rendering content), NOT in afterRender
- Custom helpers (`lt`, `abs`, `gte`) must be registered via `handlebars.registerHelper()` in the helpers editor
- All sizes use `vw` units for responsive scaling across different screen sizes
- The `afterRender` function runs after each data refresh — clean up previous animations (e.g., `cancelAnimationFrame`, `clearInterval`) at the start
