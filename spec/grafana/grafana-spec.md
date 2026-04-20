# Prdikov Dashboard — Complete Panel Specification

Dashboard UID: `q50mEhf7k` | Datasource: InfluxDB (`ceyru5v6xg3r4b`) | Refresh: 10s | 24-column grid

---

## Table of Contents

1. [Dashboard Architecture](#dashboard-architecture)
2. [Color Scheme](#color-scheme)
3. [Typography Scale](#typography-scale)
4. [Query Patterns](#query-patterns)
4. [Panel 70 — Weather Widget](#panel-70--weather-widget)
5. [Panel 67 — Indoor / Rooms](#panel-67--indoor--rooms)
6. [Panel 80 — Energy Topology](#panel-80--energy-topology)
7. [Panel 68 — Power Flow v6 (archived)](#panel-68--power-flow-v6)
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

### Grid Layout (v5)

Two-column layout: column 1 = 14 units (58%), column 2 = 10 units (42%).

```
Row  0-6:   [70 Outdoor (0,0,14,7)]               [67 Indoor (14,0,10,7)]
Row  7-15:  [80 Energy Topology (0,7,14,9)]        [83 Heat Tiles (14,7,10,11)]
Row 16-26:  [81 Energy Chart+Stats (0,16,14,11)]   ┃
Row 18-25:  ┃                                      [86 Vehicles (14,18,10,8)]
```

### Panel Map

| ID | Title | Type | Grid (x,y,w,h) | Notes |
|----|-------|------|-----------------|-------|
| 70 | Outdoor | `dynamictext` (canvas) | 0,0,14,7 | Weather widget with sparkline (afterRender JS) |
| 67 | Indoor | `dynamictext` | 14,0,10,7 | 5 rooms + CO2 stat-bar |
| 80 | Energy Topology | `dynamictext` (SVG) | 0,7,14,9 | Horizontal flow: Solar/Grid → Inverter → Battery/House/Wallbox |
| 81 | Energy Chart + Stats | `dynamictext` (SVG) | 0,16,14,11 | Chart (Solar/House/Battery/Bojlery + OTE + forecast) + Energy Stats (Today/Month bars, Self-suff, Virt.batt) |
| 83 | Heat Tiles | `dynamictext` | 14,7,10,11 | Krb + COP + Heat Pump tiles + TC chart + stat-bar |
| 86 | Vehicles | `dynamictext` | 14,18,10,8 | Enyaq + ID.3 with SoC bars and per-car plug status pills (Connected/Charging/Disconnected) |

Old panels (70, 67, 68, 47, 61, 2, 69, 43, 39, 50, 24, 20, 57, 36, 49, 10, 66) are archived in `spec/grafana/old/`.

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
| Temperature (outdoor) — hero value | Yellow | `#FADE2A` | Panel 70 hero number |
| Temperature (outdoor) — gradient anchor @ 10 °C | Yellow | `#F2CC0C` | C4 outdoor ladder stop only |
| Temp Hi (forecast) | Orange | `#FF9830` | Panel 70 |
| Temp Lo (forecast) | Blue | `#5794F2` | Panel 70 |
| Humidity | Blue | `#5794F2` | Panels 67, 70 |
| Rain | Purple | `#B877D9` | Panels 66, 70 |
| Wind sustained | White | `#d8d9da` | Panel 70 |
| Wind 30m max | Orange | `#FF9830` | Panel 70 |
| Wind forecast line | Blue | `#5794F2` | Panel 70 sparkline |
| Solar radiation | BlYlRd gradient | 0→1000 W/m² | Panel 70 stats bar |

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
| CO2 < 800 | `#73bf69` | Good air quality |
| CO2 800–1000 | `#FF9830` | Moderate |
| CO2 > 1000 | `#f2495c` | Poor air quality |

---

## Redesign v5 — Consolidated Color Decisions

This section locks the canonical color mapping for the v5 dashboard redesign (`redesign-v5.html`). It supersedes any ad-hoc color choices in the redesign HTML and resolves conflicts across the original panels. Decisions approved by @matej.pristak on 2026-04-19.

### Semantic tokens

| Token | Hex | Canonical role |
|---|---|---|
| `--red` | `#f2495c` | Error / over-threshold / discharge-alarm |
| `--orange` | `#FF9830` | Warning / bojlery (hot water) / return temp / wallbox active |
| `--orange-red` | `#FF6B3D` | Battery/Car SoC 10–20% tier |
| `--yellow` | `#FADE2A` | Battery kW (charge/discharge) / inverter-temp 40–50 °C |
| `--green` | `#73bf69` | House consumption / SoC green tier (30–90) / OK / OTE cheap |
| `--green-dark` | `#37872D` | Heat-pump flow / target temp |
| `--green-deep` | `#4a9e3f` | Solar production tier 2–4 kW |
| `--green-light` | `#a6e09e` | Solar production tier 0–2 kW |
| `--blue` | `#5794F2` | Solar identity / humidity / SoC top tier (>90) / forecast low |
| `--blue-light` | `#73C0F5` | Solar production tier 4–6 kW / grid export mild |
| `--blue-dark` | `#3d6fd4` | Solar production tier >8 kW |
| `--purple` | `#B877D9` | Rain (only — not reused) |
| `--dim` | `#8e8e8e` | Dim labels / idle values |
| `--muted` | `#555` | Zero-line / heavily muted decoration |
| `--text` | `#d8d9da` | Primary text |
| `--bg` | `#181b1f` | Panel background |
| `--card` / `--card-2` / `--card-3` | `#1e2228` / `#1a1d22` / `#15181c` | Card fills |

### Solar / PV production — 6-tier ladder (C1)

**Visualization:** 20-bar ladder at the card background (1 bar = 500 W, max 10 kW). Each bar is colored by its own tier; lit bars (≤ current output) at opacity .32, partial bar at .18, dim at .06.

| kW range | Hex | Tier |
|---|---|---|
| 0–1 kW | `#a6e09e` | Tier 1 — light green |
| 1–2 kW | `#73bf69` | Tier 2 — green |
| 2–4 kW | `#4a9e3f` | Tier 3 — deep green |
| 4–6 kW | `#73C0F5` | Tier 4 — light blue |
| 6–8 kW | `#5794F2` | Tier 5 — blue |
| > 8 kW | `#3d6fd4` | Tier 6 — dark blue |

Solar **identity color** (card stroke, icon, kW value, flow arrow) = `#5794F2`. Only the ladder bars change with intensity.

### Battery flow (kW, signed) (C2)

Canonical yellow for battery-direction visualization: **`#FADE2A`**. Retires panel-2's `#F2CC0C`. Applies to: battery card stroke, battery kW value, flow arrow Inverter→Battery, inverter allocation-bar battery segment.

### Battery SoC ramp (earlier decision, C12)

20-piece strip inside battery card (each piece = 5%). Lit pieces use the current-tier color from the ramp below; dim pieces use the same hue at low opacity.

| SoC | Hex |
|---|---|
| > 90% | `#5794F2` |
| 30–90% | `#73bf69` |
| 20–30% | `#FF9830` |
| 10–20% | `#FF6B3D` |
| < 10% | `#f2495c` |

### Grid state coloring (C3)

| State | Text / value color | When |
|---|---|---|
| Idle / balanced | `#a8a9aa` (neutral) | \|kW\| < 0.1 |
| Import (buying) | `#f2495c` | kW > +0.1 |
| Export (selling) | `#73bf69` | kW < −0.1 |

Card stroke stays neutral `#a8a9aa` at .45 opacity to preserve card identity.

### Grid — 20-bar diverging ladder

10 bars left of a zero-marker (export) + 10 bars right (import). 1 bar = 1 kW, range ±10 kW. Bars color-coded by their own tier regardless of current kW; lit bars (between zero and current draw) at opacity .32, partial bar at .18, rest dim at .06. Zero marker is a 1 px `#d8d9da` line at opacity .35.

**Export half (left, greens, mild → heavy):**

| kW range | Hex |
|---|---|
| 0 – 2 kW | `#a6e09e` light green |
| 2 – 4 kW | `#73bf69` green |
| 4 – 6 kW | `#4a9e3f` deep green |
| > 6 kW | `#37872D` dark green |

**Import half (right, yellow → red, mild → heavy):**

| kW range | Hex |
|---|---|
| 0 – 2 kW | `#FADE2A` yellow |
| 2 – 4 kW | `#FF9830` orange |
| 4 – 6 kW | `#FF6B3D` orange-red |
| > 6 kW | `#f2495c` red |

Approved 2026-04-19 — supersedes the older 3-band "mild/moderate/heavy" spec at lines 148-153.

### Outdoor temperature — 5-tier ladder (C4)

From panel 70, adopted verbatim:

| Range | Hex |
|---|---|
| ≤ −10 °C | `#1565C0` |
| 0 °C | `#4fc3f7` |
| 10 °C | `#f2cc0c` |
| 20 °C | `#FF9830` |
| ≥ 30 °C | `#f2495c` |

Interpolate linearly between anchors.

### Indoor temperature — 10-step ramp (C5)

From panel 67, adopted verbatim (see "Indoor Temperature Color Gradient" table above).

### CO₂ thresholds (C6)

Bug fix: 1025 ppm must render `#f2495c` red (was rendering orange in redesign). Thresholds remain per the UI Colors table above: `<800 #73bf69 · 800–1000 #FF9830 · >1000 #f2495c`.

### Humidity (C7)

Unified to **`#5794F2`** across all panels (indoor + weather). Retires panel-67's `#6e9fff`.

### Solar radiation — 4-tier thresholds (C8)

New tiering:

| W/m² | Hex |
|---|---|
| < 200 | `#73bf69` (green) |
| 200–399 | `#FADE2A` (yellow) |
| 400–599 | `#FF9830` (orange) |
| ≥ 600 | `#f2495c` (red) |

### Heat-pump / TC temperatures (C9, revised for Heating panel)

| Metric | Hex | Source | Notes |
|---|---|---|---|
| Target temp | `#73bf69` (green) | panel 47 | Shown in Heat-Pump tile as "out" value and in the stat-bar below the chart |
| Water temp (bečka) | `#FADE2A` (yellow) | panel 47 | Shown in Heat-Pump tile as "in" value and in the stat-bar; also used for the lower line in the TC chart |

Chart legend above the TC graph has been removed; the stat-bar carries the series identity. Orange was retired here to avoid a three-way collision with wallbox and consumption oranges, and to lock "water temp = yellow" as a panel-wide convention.

### Car / EV SoC — 5-tier ramp + fixed-band bar (C10)

Mirrors the Battery SoC ramp exactly:

| SoC | Hex |
|---|---|
| > 90% | `#5794F2` |
| 30–90% | `#73bf69` |
| 20–30% | `#FF9830` |
| 10–20% | `#FF6B3D` |
| < 10% | `#f2495c` |

Retires panel-61's 3-step ramp. Purple `#B877D9` no longer used for cars — reserved exclusively for rain.

**Bar rendering (panel-61 technique, hard bands):** the SoC bar carries a full-width gradient with **hard stops** at 10 / 20 / 30 / 90 %, so each tier occupies a fixed width of the track regardless of current SoC. An opaque cover (width = 100 − SoC %) is drawn on top of the unfilled right portion. This prevents the earlier behaviour where the whole red-orange-green ramp stretched to fit the fill width; instead, each colour band has a constant on-screen length and the current SoC is communicated by where the cover starts.

CSS stops:
```
linear-gradient(90deg,
  #f2495c 0%,  #f2495c 10%,
  #FF6B3D 10%, #FF6B3D 20%,
  #FF9830 20%, #FF9830 30%,
  #73bf69 30%, #73bf69 90%,
  #5794F2 90%, #5794F2 100%);
```

**Charging pulse:** `@keyframes car-pulse { 0,100% {opacity:1} 50% {opacity:.4} }`, 2 s ease-in-out, ported from `panel-61-cars.jsx`. Applied to the gradient layer only so the target marker and label stay static.

### Hot water (bojlery) (C11)

Reserved color: **`#FF9830`** (same as panel 2). No other metric uses this hue in the boiler context.

### House — 20-bar consumption ladder

1 bar = 500 W, 20 bars = 10 kW max. Same rendering mechanics as Solar (lit .32 / partial .18 / dim .06). Tier colors verbatim from the "House consumption" table above:

| kW range | Bars (0-indexed) | Hex |
|---|---|---|
| 0 – 2 kW | 0 – 3 | `#73bf69` green |
| 2 – 4 kW | 4 – 7 | `#FADE2A` yellow |
| 4 – 6 kW | 8 – 11 | `#FF9830` orange |
| > 6 kW | 12 – 19 | `#f2495c` red |

House identity (card stroke, icon, kW value) stays `#73bf69`.

### Wallbox — 20-bar charging ladder

1 bar = 500 W, 20 bars = 10 kW max (covers 3-phase 16 A ≈ 11 kW). Approved 2026-04-19 — original panels only defined active/inactive, so this is a new decision.

| kW range | Bars (0-indexed) | Hex |
|---|---|---|
| 0 – 4 kW | 0 – 7 | `#FADE2A` yellow |
| 4 – 8 kW | 8 – 15 | `#FF9830` orange |
| > 8 kW | 16 – 19 | `#f2495c` red |

**Disconnected state:** when no car is connected, render all 20 bars at `#4a4a4a` opacity .06 (overrides tier colors entirely). Card stroke `#6a6a6a` at opacity .5 when idle / disconnected; flips to `#FF9830` when charging draw > 0.

### Inverter alerts & temperature (earlier decisions, revised)

**Header** — only the `⚙ INVERTER` caption. The `hybrid 10 kW` capacity sub-label has been removed; alert-state semantics now live entirely in the phase-balance bar (where the offending phase is colour-coded red) and in the diagnostic-message stripe at the bottom of the card.

**Inverter temperature thresholds** — bottom-left of card:
| Range | Hex |
|---|---|
| ≤ 40 °C | `#73bf69` |
| 41–50 °C | `#FADE2A` |
| 51–60 °C | `#FF9830` |
| > 60 °C | `#f2495c` |

**Diagnostic message** — bottom-right of card, adjacent to temperature. Source: **Panel 36 FVE.diag**.
- Normal operation (code < 80): `#73BF69` green, pulsing LED-style status dot, message text e.g. "Normal operation"
- Fault (code ≥ 80): `#f2495c` red, same pulse, diagnostic string from inverter
- Font: 15 px, weight 700
- LED dot: `r=4.5`, 2.4 s opacity pulse animation (1 → 0.4 → 1)

### Inverter — Phase Balance Bar (big bar, 3 segments)

Replaces the earlier BATT/HOUSE allocation bar. Source: **Panel 50 FVE Phases** (L1/L2/L3 live load in kW).

**Layout** — three equal segments inside a `324 × 48` container:

| Seg | x | width | corners |
|---|---|---|---|
| L1 | 0 | 106 | `rx=6` (outer left) |
| L2 | 109 | 106 | no rx (middle) |
| L3 | 218 | 106 | `rx=6` (outer right) |

3-px visual gaps at x=106–109 and x=215–218 create natural "chip" separation at the seams. Each segment is independently color-coded by its own kW load.

**Per-phase tier (each of L1/L2/L3 evaluated independently):**
| kW | Hex |
|---|---|
| ≤ 1 kW | `#73bf69` green |
| 1 – 2 kW | `#FADE2A` yellow |
| 2 – 3 kW | `#FF9830` orange |
| > 3 kW | `#f2495c` red — over-threshold; phase visually flagged in the bar |

**Per-segment text (dark `#0a0c0e` on bright tier fills, centered):**
- Phase label at y=21, font-size 12, letter-spacing 1.4, weight 800 ("L1" / "L2" / "L3")
- kW value at y=40, font-size 17 weight 800, with inline 10-px " kW" tspan

**Rationale:** surfaces which phase is the source of an overcurrent condition at a glance, and preserves the operator's ability to spot heavy-phase asymmetry at a distance on the tablet. Over-threshold colouring lives in the bar itself — there is no separate capacity title string (the v5 header is just `⚙ INVERTER`).

### Heating panel — top-row tiles (revised)

Three tiles, left to right: **Krb · COP · Heat Pump**. Chart legend above the TC graph is removed; identity is carried by the stat-bar below the chart.

**Krb tile** (fireplace):
- Caption: `Krb` (no "Fireplace ·" prefix)
- Status pill top-right — 4-state colour per the **Status pills → Krb (fireplace)** table below (gray/red/green/orange by ON/OFF × body-temp band). The simple 2-colour "green when `krb_w > 20`, red otherwise" rule is retired.
- Current body temp: big green value (e.g. 21.1°)
- Rate of change ("per hour" cool/heat): prominent 28 px blue, right of the temp, arrow glyph (`↓` cooling, `↑` heating) + value + `°/h` unit
- `last fire` timestamp **removed** — not available in current data setup

**COP tile:**
- Caption: `COP · 24h`
- Big value coloured from the continuous Red→Yellow→Green gradient of Panel 49 (`panel-49-cop.jsx`), mapped 0…5. 4.49 → `--green-deep` (#4a9e3f)
- Inline 3-hour delta to the right of the big value: 20 px arrow + value (↑ 0.18) followed by muted `last 3h` caption. Arrow colour tracks direction (↑ green, ↓ red, flat dim)
- Other subtext (target / "excellent") removed

**Heat Pump tile:**
- Caption: `Heat Pump`, Running/Idle pill top-right
- Two paired temps, 32 px each, separated by slash:
  - `out` (heated feed going out to the loop) — always **yellow** `#FADE2A`
  - `in` (cooler water returning from the loop) — always **blue** `#5794F2`
- These colours are **fixed** to the in/out semantic and are deliberately independent of the chart series below (which uses green = target temp, yellow = water temp)
- All other subtext removed

**TC water-temp chart:**
- No legend, no title bar
- Two lines: green `#73bf69` (target temp, upper band) and yellow `#FADE2A` (water temp, lower band)

**Stat-bar below chart:**
| Slot | Label | Color |
|---|---|---|
| 1 | `Target temp` | `#73bf69` green |
| 2 | `Water temp` | `#FADE2A` yellow |
| 3 | `Δ` | default text |
| 4 | `Trend 1h` | `#5794F2` blue |

Both trend indicators on this panel — the Krb rate-of-change (`↓ 0.3 °/h`) and the TC water `Trend 1h` — are hourly trends, sourced over the same 1-hour window, so their formatting and cadence stay in sync.

### OTE price tiers (earlier, C-lock)

Discrete 3-tier (retains panel-69 gradient endpoints):
| Kč/kWh | Hex |
|---|---|
| < 0.5 | `#73bf69` (cheap) |
| 0.5–2.0 | `#FF9830` (medium) |
| ≥ 2.0 | `#f2495c` (expensive) |

### Rain (locked)

`#B877D9` — used only for rain volume / rain sparkline. Not reused for any other role.

### Status pills — canonical per-entity states

Consolidated state vocabulary and colours for the status pills used across the redesign. Approved by @matej.pristak 2026-04-19. All pills follow the standard `.pill` chip shape; the coloured dot to the left of the label matches the pill tint.

**Cars (wallbox / EV)**
| State | Colour | Hex | Trigger |
|---|---|---|---|
| `CHARGING` | Orange | `#FF9830` | `charging_wallbox_power > 0` |
| `CONNECTED` | Green | `#73bf69` | Cable plugged, not drawing power |
| `DISCONNECTED` | Gray | `#6a6a6a` | No cable / idle |

**Heat pump**
| State | Colour | Hex | Trigger |
|---|---|---|---|
| `ON` | Green | `#73bf69` | Compressor running |
| `OFF` | Gray | `#6a6a6a` | Idle / standby |

**Krb (fireplace)** — colour depends on both ON/OFF state and body temperature:
| State | Condition | Colour | Hex |
|---|---|---|---|
| `OFF` | body temp < 30 °C | Gray | `#6a6a6a` |
| `OFF` | body temp ≥ 30 °C | Red | `#f2495c` |
| `ON` | body temp < 65 °C | Green | `#73bf69` |
| `ON` | body temp ≥ 65 °C | Orange | `#FF9830` |

Rationale: residual hot mass after shutdown (OFF + hot) is surfaced in red as a safety cue; running hot (ON + ≥ 65 °C) is surfaced in orange so it's visibly distinct from steady-state green.

**Rooms (indoor heating zones)**
| State | Colour | Hex | Trigger |
|---|---|---|---|
| `IDLE` | Gray | `#6a6a6a` | Zone at/above setpoint, no call for heat |
| `HEATING` | Orange | `#FF9830` | Zone below setpoint, actively calling for heat |

Supersedes the earlier `Krb ON/OFF` pair in the UI Colors table (which used a simple two-colour mapping without the temperature bands).

---

## Typography Scale

Six-tier scale derived from the Outdoor panel. Use these tokens consistently across every panel; do not introduce one-off sizes.

### Scale tokens

| Token | px | Canonical source | Role |
|-------|----|------------------|------|
| **XL** | 110 | Outdoor hero temperature (`.wx-temp-group .num`) | Dashboard-wide hero — one per dashboard |
| **L**  | 64  | Outdoor clock (`.wx-clock .time`) | Primary panel metric |
| **M**  | 44  | Outdoor stats value (`.wx-stats .val`, e.g. humidity) | Key stat / secondary hero |
| **S**  | 30  | Car SoC (`.car-soc`), generic stat-bar value (`.stat-bar .s .val`) | Tertiary stat / stat-bar values |
| **XS** | 22  | Room humidity (`.room .hum`) | Inline values, big captions, deltas |
| **micro** | 11 | Graph tick labels, stat-bar labels (`.stat-bar .s .lab`) | Axis ticks, uppercase captions |

**Rules**
- **XL is reserved for the Outdoor temperature hero.** No other panel should use XL.
- Each panel has at most one L-sized number (the panel hero).
- Numbers below micro (9–10px) are only acceptable for inline markers/badges on charts (e.g. the `TARGET 80%` chip above the car SoC bar).
- Line-height 1.0 for XL/L; 1.15 for M; default for S and below.
- Units (`°`, `%`, `kWh`, etc.) next to a big number render ~40–50 % of the parent size, in `--dim`.

### Per-panel mapping

**Outdoor (reference panel)**
- Temperature hero `12.3°` → **XL** (110)
- Clock `16:16` → **L** (64)
- Humidity / Wind / Rain stat values → **M** (44)
- Hi / Lo temperatures → **S** (30)
- Date under clock → **S** (30)
- Stat sub-values (`/2`, `6/7`) → **XS** (22)

**Indoor / Rooms**
- Room temperature `21.3°` → **M** (44)
- Room name → **S** (30)
- Room humidity → **S** (30)
- Target chip → **micro** (~11)
- Stat-bar CO₂ value → **40px** (inline with label)

**Energy — topology + chart + stat-bar**
- Inverter / topology node values (solar kW, batt kW, house kW) → **M** (44)
- Stat-bar Self-suff / Virt.batt values → **S** (30)
- Diverging cons / prod numbers → **S** (30)
- Diverging delta `+3.3 / −61` → **XS** (22)
- Chart axis ticks, legends → **micro** (11)

**Heating**
- Heat-tile primary (`21.1°`, `44.9`, Pump pill) → **L** (64)
- Stat-bar flow / return / Δ → **S** (30)
- Sub-captions / trend labels → **micro** (~11–13)

**Vehicles**
- Car name (`Enyaq`, `ID.3`) → **M** (44)
- SoC `67%` → **S** (30)
- Range / max / status / timeleft → **S** (30) — bumped from micro for tablet-in-sunlight legibility
- Charge timeleft is rendered **unconverted in minutes** (e.g. `~640 min`), matching the raw `charging_time_left_*` field unit — no hours/minutes split, no amperage, no "to full" prefix
- Status pills use **per-car plug state** from vehicle API (`plug_connected_enyaq`, `plug_connected_vw`): Charging (orange `pill-car-chg`), Connected (green `pill-car-conn`), Disconnected (gray `pill-car-disc`)
- Target label above marker → **micro** (~9–11)

Any new panel must declare its mapping against this scale before being implemented.

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
│ Humidity  │  Wind    km/h  30m   km/h  │  Rain                        │ Solar │
│ 72%       │  12 / 18      15 / 22      │  0.0 mm/h  2.1 fc  4.2 tot  │ 487 W/m² │
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

// Solar radiation (current)
solarRad — weather.solarRadiation (last)

// Output: single row
array.from(rows: [{
  temp, hi, lo, humidity, rain_fc, rain_rate, rain_total,
  wind, gust, wind_30m, gust_30m,
  hourly (string), rain_hourly (string), wind_hourly (string),
  solar_radiation
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
  - Temperature line with continuous color gradient (dark blue → light blue → yellow → orange → red) based on hourly temperature values, area fill uses same gradient at 15% opacity
  - Purple rain bars (#B877D9) with opacity proportional to amount
  - Blue wind line (#5794F2, opacity 0.6)
  - Now marker: temperature-colored dot + dashed vertical line (color matches current interpolated temperature)
  - Hi/Lo peak labels (orange/blue)
  - Hour labels every 3h
- **Stats bar:** 3-section flex layout with separators
  - Humidity (flex: 0.67): blue value
  - Wind: current + 30m max (white / orange), slash notation with gusts
  - Rain: rate (mm/h) + forecast (fc) + total (tot), all purple

### Color Logic

| Element | Condition | Color |
|---------|-----------|-------|
| Temperature text | ≤ -10°C | `#1565C0` (dark blue) |
| Temperature text | 0°C | `#4fc3f7` (light blue) |
| Temperature text | 10°C | `#f2cc0c` (yellow) |
| Temperature text | 20°C | `#FF9830` (orange) |
| Temperature text | ≥ 30°C | `#f2495c` (red) |
| Temperature text | intermediate | continuous RGB interpolation between stops |
| Temp sparkline | per-hour | horizontal SVG gradient using same 5-stop scale |
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

**Bottom stat-bar — CO₂ (inline layout):**
Layout: label inline (same row) with value. Value at 40px, label at 11px uppercase.
- **CO₂**: value in ppm, color-coded (green <800, orange 800-1000, red >1000)

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

## Panel 80 — Energy Topology

**Type:** Business Text (SVG via afterRender JS)
**Grid:** (0,7,14,9) — left column, below weather

### Layout

Horizontal flow diagram: sources on left, inverter hub in center, consumers on right.

```
┌──────────┐          ┌──────────────────────┐          ┌──────────────┐
│  SOLAR   │  ──▶──▶  │      INVERTER        │  ──▶──▶  │   BATTERY    │
│  8.81 kW │          │  ┌────┬────┬────┐    │          │ -7.1 kW  39% │
└──────────┘          │  │ L1 │ L2 │ L3 │    │          └──────────────┘
┌──────────┐          │  └────┴────┴────┘    │          ┌──────────────┐
│   GRID   │  ──▶──▶  │                      │  ──▶──▶  │    HOUSE     │
│  0.06 kW │          │  temp 48°C ● Normal   │          │   1.57 kW    │
└──────────┘          └──────────────────────┘          ┌──────────────┐
                                                ──▶──▶  │   WALLBOX    │
                                                        │    0 kW      │
                                                        └──────────────┘
```

### SVG Structure (viewBox 870×248)

**Cards** — rounded `<rect>` with dark fill `#1b1e22` and colored borders:
- Solar (x=10, y=8, 200×102) — border `#5794F2`
- Grid (x=10, y=130, 200×102) — border `#a8a9aa`
- Inverter (x=250, y=20, 350×210) — border `#a8a9aa`, fill `#15181c`
- Battery (x=640, y=8, 220×70) — border `#FADE2A`
- House (x=640, y=88, 220×70) — border `#73bf69`
- Wallbox (x=640, y=168, 220×70) — border `#6a6a6a`

**Ladder bars** — 20 thin vertical `<rect>` bars inside each card, opacity toggled by afterRender JS:
- Solar: green→blue gradient (20 bars, lit count = `prod * 2`)
- Grid: diverging green/yellow/orange/red with center divider line (export left, import right)
- Battery: uniform color from 5-tier SoC scale (lit count = `soc / 5`)
- House: green→yellow→orange→red gradient (lit count = `cons * 2`)
- Wallbox: yellow→orange→red gradient (lit count = `charge * 2`)
- Lit opacity: `0.6`, unlit: `0.07`

**Text positioning** — all labels and values use `text-anchor="middle"` centered on card:
- Solar/Grid: centered at x=110 (card center of x=10..210)
- Battery label: centered at x=750; kW left-aligned x=654, SoC right-aligned x=848
- House/Wallbox: centered at x=750 (card center of x=640..860)

**Text contrast** — value text uses `paint-order="stroke fill"` with dark outline to stay readable against lit bars:
```
paint-order="stroke fill" stroke="#0a0c0e" stroke-width="3" stroke-linejoin="round"
```
Applied to: Solar value (48px), Grid value (48px), Battery kW (33px), Battery SoC (33px), House value (33px), Wallbox value (20px, stroke-width 2.5).

**Animated arrows** — dashed `<path>` lines between cards with `<marker>` arrowheads:
- Solar→Inverter: blue `#5794F2`, `flow-solar` animation (0.75s march)
- Grid→Inverter: bidirectional (green `#73bf69` when exporting, red `#f2495c` when importing)
- Inverter→Battery: yellow `#FADE2A`, `flow-batt` animation (0.70s march), direction flips when charging
- Inverter→House: green `#73bf69`, `flow-house` animation (1.10s march)
- Inverter→Wallbox: orange `#FF9830` when active, muted `#6a6a6a` when idle
- Stroke width scales with power: `min(2 + kW * 1.5, 12)`

**Inverter hub** — contains:
- Phase balance bar: 3 adjacent `<rect>` (L1/L2/L3), colored by kW tier (green <1, yellow <2, orange <3, red ≥3)
- Temperature + diagnostic status line at bottom

### Phase Color Tiers

| Load | Color | Hex |
|------|-------|-----|
| > 3 kW | Red | `#f2495c` |
| > 2 kW | Orange | `#FF9830` |
| > 1 kW | Yellow | `#FADE2A` |
| ≤ 1 kW | Green | `#73bf69` |

### Battery SoC Color Tiers

| SoC | Color | Hex |
|-----|-------|-----|
| > 90% | Blue | `#5794F2` |
| ≥ 30% | Green | `#73BF69` |
| ≥ 20% | Orange | `#FF9830` |
| ≥ 10% | Red-orange | `#FF6B3D` |
| < 10% | Red | `#F2495C` |

### Flux Query

Same query as old Panel 68 — reads live FVE, battery, meter, wallbox, phase loads, inverter temp. Additionally includes phase load fields (`load_p1`, `load_p2`, `load_p3`) and `inv_temp`.

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

This section describes the v5 target state. It supersedes the original Grafana library panel (3-stop red-green-purple soft gradient, in-bar 2-line layout). The implementation in `redesign-v5.html` is authoritative.

### Layout (v5)

Each car renders as a two-or-three-row card:

```
┌─────────────────────────────────────────────────────────────┐
│ Enyaq   [████████████████░░░░░░░░] ▌TARGET 80%       67%    │
│         277 km   max 413 km                  [DISCONNECTED] │
│         Hlavní 42, Praha                                     │
├─────────────────────────────────────────────────────────────┤
│ ID.3    [████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒] ▌TARGET 80%       30%    │
│         152 km   max 507 km   ~640 min         [CHARGING]   │
│         Vinohradská 12, Praha                                │
└─────────────────────────────────────────────────────────────┘
```

Row 1: car name · SoC bar (with TARGET marker + label) · SoC %.
Row 2: range · max range · optional charge time-left · status pill.
Row 3 (conditional): reverse-geocoded address from car GPS coordinates (hidden when empty).

### Flux Query

```flux
import "math"
import "array"

// Per-car: soc, range, time_left
// Union + pivot pattern to build 2 rows

// Shared wallbox power (safe union+default)
// Default time_left rows (0.0)

// Computed: max_range = range / soc * 100

// Per-car address (string, from diag/Car/address_* via Nominatim geocoding)
// Output: 1 row with car, soc, range, max_range, charge_w, time_left, target_soc, addr
```

### SoC Bar Design (v5, fixed-band technique)

The bar track is full width (100 %) and carries a hard-stop gradient — each tier has a fixed on-screen width regardless of SoC. An opaque cover sits on the right (width = 100 − SoC %) and hides the unfilled portion. Hard stops at 10 / 20 / 30 / 90 %:

```
linear-gradient(90deg,
  #f2495c 0%,  #f2495c 10%,
  #FF6B3D 10%, #FF6B3D 20%,
  #FF9830 20%, #FF9830 30%,
  #73bf69 30%, #73bf69 90%,
  #5794F2 90%, #5794F2 100%);
```

Bar height is 20 px (border-radius 10 px). A yellow TARGET marker (`#FADE2A`, 3 × 28 px, overflows the bar top/bottom) sits at the target-SoC position, with a 9 px `TARGET 80%` chip above.

**Charging animation** (ported from `panel-61-cars.jsx`): `@keyframes car-pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }`, 2 s ease-in-out, applied to the gradient layer only so the cover, target marker, and target label stay static.

### SoC text colour (C10)

The SoC % number follows the same 5-tier ramp as the bar:

| SoC Range | Color | Hex |
|-----------|-------|-----|
| > 90% | Blue | `#5794F2` |
| 30–90% | Green | `#73BF69` |
| 20–30% | Orange | `#FF9830` |
| 10–20% | Orange-red | `#FF6B3D` |
| < 10% | Red | `#F2495C` |

### Status pill (row 2, right-aligned)

Per the **Status pills → Cars (wallbox / EV)** table: `CHARGING` (orange), `CONNECTED` (green), `DISCONNECTED` (gray). Pill uses the standard `.pill` chip with a coloured dot.

### Stats row (row 2)

- **Range** always shown (plain text colour)
- **Max range** always shown, dim (`#8e8e8e`)
- **Time left** shown only when `time_left > 0`, orange (`#FF9830`), rendered **unconverted in minutes** (e.g. `~640 min`) — no hours/minutes split, no amperage, no "to full" prefix
- `charge_w` is in query output but not displayed (used by power flow panel)

### Address row (row 3)

- **Address** shown only when `enyaq_addr` / `vw_addr` is non-empty (Handlebars `{{#if}}`)
- Dim text (`#8e8e8e`, 13 px), single line with `text-overflow: ellipsis`
- Data pipeline: `skoda.py` → GPS lat/lon → Nominatim reverse geocode (cached per ~100 m) → MQTT `diag/Car/address_*` → Telegraf (string consumer) → InfluxDB `Car.address_enyaq` / `Car.address_vw` → Flux query (7-day range) → Handlebars template

### Typography (v5)

| Element | Token | px |
|---|---|---|
| Car name (`Enyaq`, `ID.3`) | M | 24 |
| SoC `67%` | S | 20 |
| Range / max / status / timeleft | S | 18 |
| Address | XS | 13 |
| `TARGET 80%` label | micro | ~9 |

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
| `in_temp` | Return water temperature (cooler, from loop) | °C |
| `out_temp` | Supply water temperature (heated, to loop) | °C |
| `compressor_on` | Compressor running — water or heating circuit (float 0/1) | 0/1 |
| `coil_on` | Backup coil/heater running — water or heating circuit (float 0/1) | 0/1 |
| `compressor_active` | Compressor running (boolean via `bool/` prefix, legacy) | bool |

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
| `plug_connected_enyaq` | Enyaq cable plugged in (1=yes, 0=no) | bool |
| `plug_connected_vw` | ID.3 cable plugged in (1=yes, 0=no) | bool |
| `target_soc_enyaq` | Enyaq charging target SoC | % |
| `target_soc_vw` | ID.3 charging target SoC | % |
| `charging_wallbox_power` | Wallbox charge power (shared) | W |
| `car_connected` | Any car plugged into wallbox (1=yes, 0=no) | bool |

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
| `curr` | `phase` (1/2/3) | Phase current | A |
| `load_p` | `phase` (1/2/3) | Phase load power | W |
| `inverter_temp_air` | — | Inverter air temperature | °C |
| `inverter_temp_rad` | — | Inverter radiator temperature | °C |
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
