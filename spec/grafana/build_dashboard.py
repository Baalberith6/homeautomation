#!/usr/bin/env python3
"""
Build the Prdikov Grafana dashboard JSON (v5 redesign).

Loads the existing prdikov.json, keeps meta/templating/annotations,
replaces all panels with the new 9-panel layout, and writes back.

Usage:
    python3 spec/grafana/build_dashboard.py
"""

import json
import copy
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_PATH = os.path.join(SCRIPT_DIR, "prdikov.json")

DS_UID = "ceyru5v6xg3r4b"
DS = {"type": "influxdb", "uid": DS_UID}

# ---------------------------------------------------------------------------
# Helper: Business Text panel
# ---------------------------------------------------------------------------

def business_text_panel(panel_id, grid_pos, targets, content,
                        helpers="", after_render="", styles="", title=""):
    """Create a Business Text (marcusolsson-dynamictext-panel) panel dict."""
    return {
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": 0}],
                }
            },
            "overrides": [],
        },
        "gridPos": grid_pos,
        "id": panel_id,
        "options": {
            "afterRender": after_render,
            "content": content,
            "contentPartials": [],
            "defaultContent": "",
            "editor": {"format": "auto", "language": "html"},
            "editors": [],
            "externalStyles": [],
            "helpers": helpers,
            "renderMode": "everyRow",
            "styles": styles,
            "wrap": True,
        },
        "pluginVersion": "6.2.0",
        "targets": targets,
        "title": title,
        "transparent": True,
        "type": "marcusolsson-dynamictext-panel",
    }


# ---------------------------------------------------------------------------
# Helper: Timeseries panel
# ---------------------------------------------------------------------------

def timeseries_panel(panel_id, grid_pos, targets, overrides,
                     title="", line_width=2, fill_opacity=15,
                     legend_mode="list", legend_calcs=None,
                     show_legend=True, max_data_points=None):
    """Create a native Grafana timeseries panel dict."""
    if legend_calcs is None:
        legend_calcs = ["lastNotNull"]

    legend = {
        "calcs": legend_calcs,
        "displayMode": legend_mode,
        "placement": "bottom",
    }
    if not show_legend:
        legend["displayMode"] = "hidden"

    panel = {
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False,
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "drawStyle": "line",
                    "fillOpacity": fill_opacity,
                    "gradientMode": "none",
                    "hideFrom": {
                        "legend": False,
                        "tooltip": False,
                        "viz": False,
                    },
                    "insertNulls": False,
                    "lineInterpolation": "smooth",
                    "lineWidth": line_width,
                    "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
                "unit": "short",
            },
            "overrides": overrides,
        },
        "gridPos": grid_pos,
        "id": panel_id,
        "options": {
            "legend": legend,
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "pluginVersion": "12.1.1",
        "targets": targets,
        "title": title,
        "transparent": True,
        "type": "timeseries",
    }
    if max_data_points is not None:
        panel["maxDataPoints"] = max_data_points
    return panel


def flux_target(query, ref_id="A"):
    return {"datasource": DS, "query": query, "refId": ref_id}


# ===================================================================
# PANEL 70 -- Outdoor (reuse existing, just change gridPos)
# ===================================================================

def build_panel_70(existing_panels):
    p70 = None
    for p in existing_panels:
        if p["id"] == 70:
            p70 = copy.deepcopy(p)
            break
    if p70 is None:
        raise ValueError("Panel 70 not found in existing dashboard")
    p70["gridPos"] = {"x": 0, "y": 0, "w": 15, "h": 12}
    return p70


# ===================================================================
# PANEL 67 -- Indoor Climate (reuse query, new template)
# ===================================================================

PANEL_67_CONTENT = r"""<style>
.rooms{display:flex;flex-direction:column;padding:10px 10px 6px;gap:5px;flex:1;min-height:0;font-family:'Inter','Helvetica Neue',Arial,sans-serif}
.room{flex:1;display:grid;grid-template-columns:1fr auto auto auto auto;align-items:center;column-gap:14px;padding:4px 16px;border-radius:8px;background:#1a1d22;border:1px solid rgba(255,255,255,0.06);min-height:0}
.room .name{font-size:16px;font-weight:600;color:#d8d9da}
.room .pill{min-width:72px;justify-content:center;display:inline-flex;align-items:center;gap:6px;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;border:1px solid transparent}
.pill-heat{background:rgba(255,152,48,.14);color:#FF9830;border-color:rgba(255,152,48,.28)}
.pill-idle{background:rgba(142,142,142,.10);color:#8e8e8e;border-color:rgba(142,142,142,.18)}
.pill .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.room .temp{font-size:28px;font-weight:700;line-height:1;min-width:70px;text-align:right}
.room .target{font-size:14px;color:#8e8e8e;display:flex;align-items:center;gap:3px;min-width:50px;justify-content:flex-end;font-weight:600}
.room .target::before{content:"\25b8";color:#555;margin-right:3px}
.room .hum{font-size:18px;color:#5794F2;min-width:50px;text-align:right;font-weight:700}
.room .hum.none{color:transparent;user-select:none}
.stat-bar{display:flex;background:#111217;border-top:1px solid rgba(255,255,255,0.06);flex-shrink:0}
.stat-bar .s{flex:1;padding:8px 14px;display:flex;flex-direction:column;gap:3px}
.stat-bar .s .lab{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8e8e8e;font-weight:700}
.stat-bar .s .val{font-size:24px;font-weight:700;line-height:1}
.stat-bar .s .val .unit{font-size:12px;color:#8e8e8e;margin-left:3px;font-weight:400}
</style>
<div class="rooms">
  <div class="room">
    <span class="name">Obyvacka</span>
    {{#if (gt oby_on 0)}}<span class="pill pill-heat"><span class="dot"></span>Heating</span>{{else}}<span class="pill pill-idle"><span class="dot"></span>Idle</span>{{/if}}
    <span class="temp" style="color:{{#if (gt oby_t 26)}}#f2495c{{else if (gt oby_t 25)}}#dd5d5e{{else if (gt oby_t 24)}}#b38463{{else if (gt oby_t 23)}}#88ab67{{else if (gt oby_t 20)}}#73bf69{{else if (gt oby_t 16)}}#80b368{{else if (gt oby_t 12)}}#999c65{{else if (gt oby_t 8)}}#b38463{{else if (gt oby_t 4)}}#cc6c60{{else}}#f2495c{{/if}};">{{oby_t}}&deg;</span>
    <span class="target">{{oby_set}}&deg;</span>
    <span class="hum">{{oby_h}}<span style="font-size:11px;color:#8e8e8e">%</span></span>
  </div>
  <div class="room">
    <span class="name">Pracovna</span>
    {{#if (gt pra_on 0)}}<span class="pill pill-heat"><span class="dot"></span>Heating</span>{{else}}<span class="pill pill-idle"><span class="dot"></span>Idle</span>{{/if}}
    <span class="temp" style="color:{{#if (gt pra_t 26)}}#f2495c{{else if (gt pra_t 25)}}#dd5d5e{{else if (gt pra_t 24)}}#b38463{{else if (gt pra_t 23)}}#88ab67{{else if (gt pra_t 20)}}#73bf69{{else if (gt pra_t 16)}}#80b368{{else if (gt pra_t 12)}}#999c65{{else if (gt pra_t 8)}}#b38463{{else if (gt pra_t 4)}}#cc6c60{{else}}#f2495c{{/if}};">{{pra_t}}&deg;</span>
    <span class="target">{{pra_set}}&deg;</span>
    <span class="hum">{{pra_h}}<span style="font-size:11px;color:#8e8e8e">%</span></span>
  </div>
  <div class="room">
    <span class="name">Julinka</span>
    {{#if (gt jul_on 0)}}<span class="pill pill-heat"><span class="dot"></span>Heating</span>{{else}}<span class="pill pill-idle"><span class="dot"></span>Idle</span>{{/if}}
    <span class="temp" style="color:{{#if (gt jul_t 26)}}#f2495c{{else if (gt jul_t 25)}}#dd5d5e{{else if (gt jul_t 24)}}#b38463{{else if (gt jul_t 23)}}#88ab67{{else if (gt jul_t 20)}}#73bf69{{else if (gt jul_t 16)}}#80b368{{else if (gt jul_t 12)}}#999c65{{else if (gt jul_t 8)}}#b38463{{else if (gt jul_t 4)}}#cc6c60{{else}}#f2495c{{/if}};">{{jul_t}}&deg;</span>
    <span class="target">{{jul_set}}&deg;</span>
    <span class="hum none">&mdash;</span>
  </div>
  <div class="room">
    <span class="name">Kubo</span>
    {{#if (gt kub_on 0)}}<span class="pill pill-heat"><span class="dot"></span>Heating</span>{{else}}<span class="pill pill-idle"><span class="dot"></span>Idle</span>{{/if}}
    <span class="temp" style="color:{{#if (gt kub_t 26)}}#f2495c{{else if (gt kub_t 25)}}#dd5d5e{{else if (gt kub_t 24)}}#b38463{{else if (gt kub_t 23)}}#88ab67{{else if (gt kub_t 20)}}#73bf69{{else if (gt kub_t 16)}}#80b368{{else if (gt kub_t 12)}}#999c65{{else if (gt kub_t 8)}}#b38463{{else if (gt kub_t 4)}}#cc6c60{{else}}#f2495c{{/if}};">{{kub_t}}&deg;</span>
    <span class="target">{{kub_set}}&deg;</span>
    <span class="hum none">&mdash;</span>
  </div>
  <div class="room">
    <span class="name">Spalna</span>
    {{#if (gt spa_on 0)}}<span class="pill pill-heat"><span class="dot"></span>Heating</span>{{else}}<span class="pill pill-idle"><span class="dot"></span>Idle</span>{{/if}}
    <span class="temp" style="color:{{#if (gt spa_t 26)}}#f2495c{{else if (gt spa_t 25)}}#dd5d5e{{else if (gt spa_t 24)}}#b38463{{else if (gt spa_t 23)}}#88ab67{{else if (gt spa_t 20)}}#73bf69{{else if (gt spa_t 16)}}#80b368{{else if (gt spa_t 12)}}#999c65{{else if (gt spa_t 8)}}#b38463{{else if (gt spa_t 4)}}#cc6c60{{else}}#f2495c{{/if}};">{{spa_t}}&deg;</span>
    <span class="target">{{spa_set}}&deg;</span>
    <span class="hum none">&mdash;</span>
  </div>
</div>
<div class="stat-bar">
  <div class="s"><span class="lab">CO&#8322;</span><span class="val" style="color:{{#if (gt co2 1000)}}#f2495c{{else if (gt co2 800)}}#FF9830{{else}}#73bf69{{/if}};">{{co2}}<span class="unit">ppm</span></span></div>
</div>"""

PANEL_67_HELPERS = (
    'handlebars.registerHelper("lt", function(a, b) '
    '{ return parseFloat(a) < parseFloat(b); });\n'
    'handlebars.registerHelper("gt", function(a, b) '
    '{ return parseFloat(a) > parseFloat(b); });'
)


def build_panel_67(existing_panels):
    # Extract the existing query from panel 67
    p67_orig = None
    for p in existing_panels:
        if p["id"] == 67:
            p67_orig = p
            break
    if p67_orig is None:
        raise ValueError("Panel 67 not found in existing dashboard")

    query = p67_orig["targets"][0]["query"]
    targets = [flux_target(query, "A")]

    return business_text_panel(
        panel_id=67,
        grid_pos={"x": 15, "y": 0, "w": 9, "h": 12},
        targets=targets,
        content=PANEL_67_CONTENT,
        helpers=PANEL_67_HELPERS,
    )


# ===================================================================
# PANEL 80 -- Energy Topology
# ===================================================================

PANEL_80_QUERY_A = r"""import "math"
import "array"
import "date"

// -- Live readings --
prod_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "power" and r.string == "all")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

cons_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "consumption")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

bat_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "battery_load")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

soc_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "soc")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Grid meter power --
meter_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
meter_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "meter_power")
  |> last()
  |> keep(columns: ["_time", "_value"])
meter_rec = union(tables: [meter_default, meter_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Wallbox --
charge_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
charge_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "charging_wallbox_power")
  |> last()
  |> keep(columns: ["_time", "_value"])
charge_rec = union(tables: [charge_default, charge_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Car connected --
conn_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
conn_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "car_connected")
  |> last()
  |> keep(columns: ["_time", "_value"])
conn_rec = union(tables: [conn_default, conn_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Daily stats --
d_cons_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "consumption_day")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

d_gen_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "generation_day")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Monthly stats --
month_start = date.truncate(t: now(), unit: 1mo)

m_cons_raw = from(bucket: "default")
  |> range(start: month_start)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "consumption_day")
  |> aggregateWindow(every: 1d, fn: max)
  |> sum()
  |> findRecord(fn: (key) => true, idx: 0)

m_gen_raw = from(bucket: "default")
  |> range(start: month_start)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "generation_day")
  |> aggregateWindow(every: 1d, fn: max)
  |> sum()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Virtual Battery (CEZ) --
vb_charge_raw = from(bucket: "default")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "cez" and r._field == "virtual_battery")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

vb_prod_raw = from(bucket: "default")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "cez" and r._field == "aggregated_production")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

vb_cons_raw = from(bucket: "default")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "cez" and r._field == "aggregated_consumption")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Phase loads --
load_p1_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
load_p1_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "load_p" and r.phase == "1")
  |> last()
  |> keep(columns: ["_time", "_value"])
load_p1_rec = union(tables: [load_p1_default, load_p1_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

load_p2_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
load_p2_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "load_p" and r.phase == "2")
  |> last()
  |> keep(columns: ["_time", "_value"])
load_p2_rec = union(tables: [load_p2_default, load_p2_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

load_p3_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
load_p3_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "load_p" and r.phase == "3")
  |> last()
  |> keep(columns: ["_time", "_value"])
load_p3_rec = union(tables: [load_p3_default, load_p3_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Inverter temperature --
inv_temp_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
inv_temp_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "inverter_temp_air")
  |> last()
  |> keep(columns: ["_time", "_value"])
inv_temp_rec = union(tables: [inv_temp_default, inv_temp_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Extract values --
prod       = if exists prod_raw._value then float(v: prod_raw._value) else 0.0
cons_total = if exists cons_raw._value then float(v: cons_raw._value) else 0.0
bat        = if exists bat_raw._value  then float(v: bat_raw._value)  else 0.0
soc        = if exists soc_raw._value  then float(v: soc_raw._value)  else 0.0
meter      = if exists meter_rec._value then float(v: meter_rec._value) else 0.0
charge     = if exists charge_rec._value then float(v: charge_rec._value) else 0.0
cons       = if cons_total - charge > 0.0 then cons_total - charge else 0.0
car_conn   = if exists conn_rec._value then float(v: conn_rec._value) else 0.0
d_cons     = if exists d_cons_raw._value then float(v: d_cons_raw._value) else 0.0
d_gen      = if exists d_gen_raw._value  then float(v: d_gen_raw._value)  else 0.0
m_cons     = if exists m_cons_raw._value then float(v: m_cons_raw._value) else 0.0
m_gen      = if exists m_gen_raw._value  then float(v: m_gen_raw._value)  else 0.0

self_suf = if d_cons > 0.0 then math.round(x: d_gen / d_cons * 100.0) else 0.0

vb_charge = if exists vb_charge_raw._value then float(v: vb_charge_raw._value) else 0.0
vb_prod   = if exists vb_prod_raw._value then float(v: vb_prod_raw._value) else 0.0
vb_cons   = if exists vb_cons_raw._value then float(v: vb_cons_raw._value) else 0.0
vb_pct    = if vb_cons > 0.0 then math.round(x: vb_prod / vb_cons * 100.0) else 0.0

// Battery time remaining
dod = float(v: ${InverterDepthOfDischarge})
min_soc = 100.0 - dod
usable_pct = if soc > min_soc then soc - min_soc else 0.0
usable_kwh = usable_pct / 100.0 * 20.0
bat_discharge_kw = if bat > 50.0 then bat / 1000.0 else 0.0
bat_hours_raw = if bat_discharge_kw > 0.0 then usable_kwh / bat_discharge_kw else 0.0
bat_hrs_v = math.floor(x: bat_hours_raw)
bat_mins_v = math.round(x: (bat_hours_raw - math.floor(x: bat_hours_raw)) * 60.0)

soc_stop = float(v: ${InverterStopChargingAt})
bat_charge_kw = if bat < -50.0 then math.abs(x: bat) / 1000.0 else 0.0
remaining_pct = if soc_stop > soc then soc_stop - soc else 0.0
remaining_kwh = remaining_pct / 100.0 * 20.0
bat_chg_hours_raw = if bat_charge_kw > 0.0 then remaining_kwh / bat_charge_kw else 0.0
bat_chg_hrs_v = math.floor(x: bat_chg_hours_raw)
bat_chg_mins_v = math.round(x: (bat_chg_hours_raw - math.floor(x: bat_chg_hours_raw)) * 60.0)

array.from(rows: [{
  prod:      math.round(x: prod / 1000.0 * 100.0) / 100.0,
  cons:      math.round(x: cons / 1000.0 * 100.0) / 100.0,
  soc:       math.round(x: soc),
  bat:       math.round(x: bat / 1000.0 * 100.0) / 100.0,
  meter:     math.round(x: meter / 1000.0 * 100.0) / 100.0,
  charge_w:  math.round(x: charge / 1000.0 * 100.0) / 100.0,
  car_conn:  math.round(x: car_conn),
  d_cons:    math.round(x: d_cons * 10.0) / 10.0,
  d_gen:     math.round(x: d_gen * 10.0) / 10.0,
  m_cons:    math.round(x: m_cons),
  m_gen:     math.round(x: m_gen),
  self_suf:  self_suf,
  vb_charge: math.round(x: vb_charge * 10.0) / 10.0,
  vb_prod:   math.round(x: vb_prod),
  vb_cons:   math.round(x: vb_cons),
  vb_pct:    vb_pct,
  bat_hrs:   bat_hrs_v,
  bat_mins:  bat_mins_v,
  bat_chg_hrs:  bat_chg_hrs_v,
  bat_chg_mins: bat_chg_mins_v,
  load_p1: math.round(x: (if exists load_p1_rec._value then float(v: load_p1_rec._value) else 0.0) / 1000.0 * 100.0) / 100.0,
  load_p2: math.round(x: (if exists load_p2_rec._value then float(v: load_p2_rec._value) else 0.0) / 1000.0 * 100.0) / 100.0,
  load_p3: math.round(x: (if exists load_p3_rec._value then float(v: load_p3_rec._value) else 0.0) / 1000.0 * 100.0) / 100.0,
  inv_temp: math.round(x: if exists inv_temp_rec._value then float(v: inv_temp_rec._value) else 0.0),
}])"""

PANEL_80_QUERY_B = r"""from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "FVE" and r._field == "diag")
  |> last()"""

PANEL_80_CONTENT = r"""<style>
.topo{font-family:'Inter','Helvetica Neue',Arial,sans-serif;color:#d8d9da;height:100%;display:flex;align-items:center;justify-content:center;overflow:hidden}
.topo svg{display:block;width:100%;height:auto}
@keyframes flow-march-16{from{stroke-dashoffset:16}to{stroke-dashoffset:0}}
@keyframes flow-march-11{from{stroke-dashoffset:11}to{stroke-dashoffset:0}}
.flow-solar{animation:flow-march-16 0.75s linear infinite}
.flow-batt{animation:flow-march-16 0.70s linear infinite}
.flow-house{animation:flow-march-11 1.10s linear infinite}
</style>
<div class="topo" id="topo-root"
  data-prod="{{prod}}" data-cons="{{cons}}" data-soc="{{soc}}"
  data-bat="{{bat}}" data-meter="{{meter}}" data-charge="{{charge_w}}"
  data-car-conn="{{car_conn}}"
  data-load-p1="{{load_p1}}" data-load-p2="{{load_p2}}" data-load-p3="{{load_p3}}"
  data-inv-temp="{{inv_temp}}">
<svg viewBox="0 0 1160 205" preserveAspectRatio="xMidYMid meet">
  <defs>
    <marker id="arr-yellow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#FADE2A"/></marker>
    <marker id="arr-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#5794F2"/></marker>
    <marker id="arr-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#73bf69"/></marker>
    <marker id="arr-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#6a6a6a"/></marker>
  </defs>

  <!-- SOLAR card -->
  <g id="topo-solar">
    <rect x="20" y="12" width="200" height="82" rx="8" fill="#1b1e22" stroke="#5794F2" stroke-opacity=".55" stroke-width="1.3"/>
    <g id="topo-solar-bars" transform="translate(30, 17)">
      <rect x="0"   y="0" width="8" height="72" rx="2" fill="#a6e09e" opacity=".14"/>
      <rect x="9"   y="0" width="8" height="72" rx="2" fill="#a6e09e" opacity=".14"/>
      <rect x="18"  y="0" width="8" height="72" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="27"  y="0" width="8" height="72" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="36"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="45"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="54"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="63"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="72"  y="0" width="8" height="72" rx="2" fill="#73C0F5" opacity=".14"/>
      <rect x="81"  y="0" width="8" height="72" rx="2" fill="#73C0F5" opacity=".14"/>
      <rect x="90"  y="0" width="8" height="72" rx="2" fill="#73C0F5" opacity=".14"/>
      <rect x="99"  y="0" width="8" height="72" rx="2" fill="#73C0F5" opacity=".14"/>
      <rect x="108" y="0" width="8" height="72" rx="2" fill="#5794F2" opacity=".14"/>
      <rect x="117" y="0" width="8" height="72" rx="2" fill="#5794F2" opacity=".14"/>
      <rect x="126" y="0" width="8" height="72" rx="2" fill="#5794F2" opacity=".14"/>
      <rect x="135" y="0" width="8" height="72" rx="2" fill="#5794F2" opacity=".14"/>
      <rect x="144" y="0" width="8" height="72" rx="2" fill="#3d6fd4" opacity=".14"/>
      <rect x="153" y="0" width="8" height="72" rx="2" fill="#3d6fd4" opacity=".14"/>
      <rect x="162" y="0" width="8" height="72" rx="2" fill="#3d6fd4" opacity=".14"/>
      <rect x="171" y="0" width="8" height="72" rx="2" fill="#3d6fd4" opacity=".14"/>
    </g>
    <text x="82" y="34" fill="#a8a9aa" font-size="11" font-weight="700" letter-spacing="1">SOLAR</text>
    <text x="82" y="74" id="topo-solar-val" fill="#5794F2" font-size="44" font-weight="800">{{prod}}<tspan fill="#8e8e8e" font-size="14" font-weight="600"> kW</tspan></text>
  </g>

  <!-- GRID card -->
  <g id="topo-grid">
    <rect x="20" y="108" width="200" height="82" rx="8" fill="#1b1e22" stroke="#a8a9aa" stroke-opacity=".45" stroke-width="1.3"/>
    <g id="topo-grid-bars" transform="translate(28, 113)">
      <rect x="0"   y="0" width="8" height="72" rx="2" fill="#37872D" opacity=".14"/>
      <rect x="9"   y="0" width="8" height="72" rx="2" fill="#37872D" opacity=".14"/>
      <rect x="18"  y="0" width="8" height="72" rx="2" fill="#37872D" opacity=".14"/>
      <rect x="27"  y="0" width="8" height="72" rx="2" fill="#37872D" opacity=".14"/>
      <rect x="36"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="45"  y="0" width="8" height="72" rx="2" fill="#4a9e3f" opacity=".14"/>
      <rect x="54"  y="0" width="8" height="72" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="63"  y="0" width="8" height="72" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="72"  y="0" width="8" height="72" rx="2" fill="#a6e09e" opacity=".14"/>
      <rect x="81"  y="0" width="8" height="72" rx="2" fill="#a6e09e" opacity=".14"/>
      <line x1="91.5" y1="-2" x2="91.5" y2="74" stroke="#d8d9da" stroke-width="1" opacity=".35"/>
      <rect x="94"  y="0" width="8" height="72" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="103" y="0" width="8" height="72" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="112" y="0" width="8" height="72" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="121" y="0" width="8" height="72" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="130" y="0" width="8" height="72" rx="2" fill="#FF6B3D" opacity=".14"/>
      <rect x="139" y="0" width="8" height="72" rx="2" fill="#FF6B3D" opacity=".14"/>
      <rect x="148" y="0" width="8" height="72" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="157" y="0" width="8" height="72" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="166" y="0" width="8" height="72" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="175" y="0" width="8" height="72" rx="2" fill="#f2495c" opacity=".14"/>
    </g>
    <text x="82" y="130" fill="#a8a9aa" font-size="11" font-weight="700" letter-spacing="1">GRID</text>
    <text x="82" y="170" id="topo-grid-val" fill="#a8a9aa" font-size="44" font-weight="800">{{meter}}<tspan fill="#8e8e8e" font-size="14" font-weight="600"> kW</tspan></text>
  </g>

  <!-- Arrow: Solar -> Inverter -->
  <path id="topo-arr-solar" d="M222,52 L400,65" stroke="#5794F2" stroke-width="2" stroke-linecap="round" fill="none" stroke-dasharray="4 5" marker-end="url(#arr-blue)" stroke-opacity=".45"/>

  <!-- Arrow: Grid -> Inverter -->
  <path id="topo-arr-grid" d="M222,149 L400,140" stroke="#6a6a6a" stroke-width="1.5" stroke-linecap="round" fill="none" stroke-dasharray="4 5" marker-end="url(#arr-muted)" stroke-opacity=".45"/>

  <!-- INVERTER hub -->
  <g id="topo-inverter">
    <rect x="400" y="28" width="360" height="148" rx="10" fill="#15181c" stroke="#a8a9aa" stroke-opacity=".55" stroke-width="1.4"/>
    <text x="418" y="52" fill="#a8a9aa" font-size="12" font-weight="700" letter-spacing="1.6">INVERTER</text>
    <!-- Phase balance bar -->
    <g transform="translate(418, 74)" id="topo-phases">
      <rect x="0" y="0" width="324" height="48" rx="6" fill="#0f1115" stroke="#2c3035" stroke-width="0.8"/>
      <rect id="topo-phase-l1" x="0" y="0" width="106" height="48" rx="6" fill="#73bf69"/>
      <text x="53" y="21" fill="#0a0c0e" font-size="12" font-weight="800" text-anchor="middle" letter-spacing="1.4">L1</text>
      <text x="53" y="40" id="topo-phase-l1-val" fill="#0a0c0e" font-size="17" font-weight="800" text-anchor="middle">{{load_p1}}<tspan font-size="10" font-weight="700"> kW</tspan></text>
      <rect id="topo-phase-l2" x="109" y="0" width="106" height="48" fill="#73bf69"/>
      <text x="162" y="21" fill="#0a0c0e" font-size="12" font-weight="800" text-anchor="middle" letter-spacing="1.4">L2</text>
      <text x="162" y="40" id="topo-phase-l2-val" fill="#0a0c0e" font-size="17" font-weight="800" text-anchor="middle">{{load_p2}}<tspan font-size="10" font-weight="700"> kW</tspan></text>
      <rect id="topo-phase-l3" x="218" y="0" width="106" height="48" rx="6" fill="#73bf69"/>
      <text x="271" y="21" fill="#0a0c0e" font-size="12" font-weight="800" text-anchor="middle" letter-spacing="1.4">L3</text>
      <text x="271" y="40" id="topo-phase-l3-val" fill="#0a0c0e" font-size="17" font-weight="800" text-anchor="middle">{{load_p3}}<tspan font-size="10" font-weight="700"> kW</tspan></text>
    </g>
    <!-- Temp + diag -->
    <text x="418" y="162" fill="#8e8e8e" font-size="13" font-weight="600" letter-spacing="0.3">temp <tspan id="topo-temp-val" fill="#73bf69" font-size="22" font-weight="800">{{inv_temp}} &deg;C</tspan></text>
    <circle id="topo-diag-dot" cx="560" cy="156" r="4.5" fill="#73BF69"/>
    <text id="topo-diag-text" x="572" y="162" fill="#73BF69" font-size="15" font-weight="700" letter-spacing="0.2">Normal operation</text>
  </g>

  <!-- Arrow: Inverter -> Battery -->
  <path id="topo-arr-bat" d="M762,72 L940,52" stroke="#FADE2A" stroke-width="2" stroke-linecap="round" fill="none" stroke-dasharray="4 5" marker-end="url(#arr-yellow)" stroke-opacity=".45"/>

  <!-- Arrow: Inverter -> House -->
  <path id="topo-arr-house" d="M762,102 L940,110" stroke="#73bf69" stroke-width="2" stroke-linecap="round" fill="none" stroke-dasharray="4 5" marker-end="url(#arr-green)" stroke-opacity=".45"/>

  <!-- Arrow: Inverter -> Wallbox -->
  <path id="topo-arr-wb" d="M762,150 L940,168" stroke="#6a6a6a" stroke-width="1.5" stroke-linecap="round" fill="none" stroke-dasharray="4 5" marker-end="url(#arr-muted)" stroke-opacity=".45"/>

  <!-- BATTERY card -->
  <g id="topo-battery">
    <rect x="940" y="12" width="210" height="56" rx="8" fill="#1b1e22" stroke="#FADE2A" stroke-opacity=".55" stroke-width="1.3"/>
    <g id="topo-bat-bars" transform="translate(945, 15)" fill="#73BF69">
      <rect x="0"   y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="10"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="20"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="30"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="40"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="50"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="60"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="70"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="80"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="90"  y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="100" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="110" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="120" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="130" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="140" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="150" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="160" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="170" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="180" y="0" width="9" height="50" rx="2" opacity=".14"/>
      <rect x="190" y="0" width="9" height="50" rx="2" opacity=".14"/>
    </g>
    <text x="954" y="22" fill="#a8a9aa" font-size="11" font-weight="700" letter-spacing="1">BATTERY</text>
    <text x="954" y="52" id="topo-bat-kw" fill="#FADE2A" font-size="30" font-weight="800">{{bat}}<tspan fill="#8e8e8e" font-size="13" font-weight="600"> kW</tspan></text>
    <text x="1136" y="52" id="topo-bat-soc" fill="#73BF69" font-size="30" font-weight="800" text-anchor="end">{{soc}}%</text>
  </g>

  <!-- HOUSE card -->
  <g id="topo-house">
    <rect x="940" y="76" width="210" height="56" rx="8" fill="#1b1e22" stroke="#73bf69" stroke-opacity=".55" stroke-width="1.3"/>
    <g id="topo-house-bars" transform="translate(945, 79)">
      <rect x="0"   y="0" width="9" height="50" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="10"  y="0" width="9" height="50" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="20"  y="0" width="9" height="50" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="30"  y="0" width="9" height="50" rx="2" fill="#73bf69" opacity=".14"/>
      <rect x="40"  y="0" width="9" height="50" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="50"  y="0" width="9" height="50" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="60"  y="0" width="9" height="50" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="70"  y="0" width="9" height="50" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="80"  y="0" width="9" height="50" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="90"  y="0" width="9" height="50" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="100" y="0" width="9" height="50" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="110" y="0" width="9" height="50" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="120" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="130" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="140" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="150" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="160" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="170" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="180" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="190" y="0" width="9" height="50" rx="2" fill="#f2495c" opacity=".14"/>
    </g>
    <text x="1000" y="92" fill="#a8a9aa" font-size="11" font-weight="700" letter-spacing="1">HOUSE</text>
    <text x="1000" y="121" id="topo-house-val" fill="#73bf69" font-size="30" font-weight="800">{{cons}}<tspan fill="#8e8e8e" font-size="13" font-weight="600"> kW</tspan></text>
  </g>

  <!-- WALLBOX card -->
  <g id="topo-wallbox">
    <rect x="940" y="140" width="210" height="50" rx="8" fill="#1b1e22" id="topo-wb-border" stroke="#6a6a6a" stroke-opacity=".5" stroke-width="1.3"/>
    <g id="topo-wb-bars" transform="translate(945, 143)">
      <rect x="0"   y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="10"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="20"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="30"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="40"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="50"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="60"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="70"  y="0" width="9" height="44" rx="2" fill="#FADE2A" opacity=".14"/>
      <rect x="80"  y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="90"  y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="100" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="110" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="120" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="130" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="140" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="150" y="0" width="9" height="44" rx="2" fill="#FF9830" opacity=".14"/>
      <rect x="160" y="0" width="9" height="44" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="170" y="0" width="9" height="44" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="180" y="0" width="9" height="44" rx="2" fill="#f2495c" opacity=".14"/>
      <rect x="190" y="0" width="9" height="44" rx="2" fill="#f2495c" opacity=".14"/>
    </g>
    <text x="1000" y="158" fill="#a8a9aa" font-size="11" font-weight="700" letter-spacing="1">WALLBOX</text>
    <text x="1000" y="178" id="topo-wb-val" fill="#8e8e8e" font-size="17" font-weight="800">{{charge_w}}<tspan font-size="10" font-weight="600"> kW</tspan></text>
  </g>
</svg>
</div>"""

PANEL_80_AFTER_RENDER = r"""var root=document.getElementById("topo-root");
if(!root)return;
var D={
  prod:parseFloat(root.dataset.prod)||0,
  cons:parseFloat(root.dataset.cons)||0,
  soc:parseFloat(root.dataset.soc)||0,
  bat:parseFloat(root.dataset.bat)||0,
  meter:parseFloat(root.dataset.meter)||0,
  charge:parseFloat(root.dataset.charge)||0,
  carConn:parseFloat(root.dataset.carConn)||0,
  lp1:parseFloat(root.dataset.loadP1)||0,
  lp2:parseFloat(root.dataset.loadP2)||0,
  lp3:parseFloat(root.dataset.loadP3)||0,
  invTemp:parseFloat(root.dataset.invTemp)||0
};

// Phase color by kW tier
function phaseColor(kw){
  if(kw>3)return"#f2495c";
  if(kw>2)return"#FF9830";
  if(kw>1)return"#FADE2A";
  return"#73bf69";
}
var l1=document.getElementById("topo-phase-l1");
var l2=document.getElementById("topo-phase-l2");
var l3=document.getElementById("topo-phase-l3");
if(l1)l1.setAttribute("fill",phaseColor(D.lp1));
if(l2)l2.setAttribute("fill",phaseColor(D.lp2));
if(l3)l3.setAttribute("fill",phaseColor(D.lp3));

// Temperature color
var tEl=document.getElementById("topo-temp-val");
if(tEl){
  var tc=D.invTemp<=40?"#73bf69":D.invTemp<=50?"#FADE2A":D.invTemp<=60?"#FF9830":"#f2495c";
  tEl.setAttribute("fill",tc);
}

// Solar arrow
var arrS=document.getElementById("topo-arr-solar");
if(arrS){
  if(D.prod>0.1){
    var sw=Math.min(2+D.prod*1.5,12);
    arrS.setAttribute("stroke-width",sw);
    arrS.setAttribute("stroke-opacity","1");
    arrS.setAttribute("stroke-dasharray","10 6");
    arrS.classList.add("flow-solar");
  }
}

// Grid arrow
var arrG=document.getElementById("topo-arr-grid");
if(arrG){
  var mAbs=Math.abs(D.meter);
  if(mAbs>0.1){
    var gw=Math.min(2+mAbs*1.5,12);
    arrG.setAttribute("stroke-width",gw);
    arrG.setAttribute("stroke-opacity","1");
    arrG.setAttribute("stroke-dasharray","10 6");
    if(D.meter>0){
      arrG.setAttribute("d","M400,140 L222,149");
      arrG.setAttribute("stroke","#73bf69");
      arrG.setAttribute("marker-end","url(#arr-green)");
    }else{
      arrG.setAttribute("stroke","#f2495c");
      arrG.setAttribute("marker-end","url(#arr-muted)");
    }
  }
}

// Battery arrow
var arrB=document.getElementById("topo-arr-bat");
if(arrB){
  var bAbs=Math.abs(D.bat);
  if(bAbs>0.1){
    var bw=Math.min(2+bAbs*1.5,12);
    arrB.setAttribute("stroke-width",bw);
    arrB.setAttribute("stroke-opacity","1");
    arrB.setAttribute("stroke-dasharray","10 6");
    arrB.classList.add("flow-batt");
    if(D.bat>0){
      arrB.setAttribute("d","M940,52 L762,72");
    }
  }
}

// House arrow
var arrH=document.getElementById("topo-arr-house");
if(arrH){
  if(D.cons>0.1){
    var hw=Math.min(2+D.cons*1.2,10);
    arrH.setAttribute("stroke-width",hw);
    arrH.setAttribute("stroke-opacity","1");
    arrH.setAttribute("stroke-dasharray","7 4");
    arrH.classList.add("flow-house");
  }
}

// Wallbox arrow
var arrW=document.getElementById("topo-arr-wb");
if(arrW&&D.charge>0.1){
  var ww=Math.min(2+D.charge*1.5,12);
  arrW.setAttribute("stroke-width",ww);
  arrW.setAttribute("stroke-opacity","1");
  arrW.setAttribute("stroke","#FF9830");
  arrW.setAttribute("marker-end","url(#arr-yellow)");
}

// Solar ladder bars
var solarBars=document.querySelectorAll("#topo-solar-bars rect");
if(solarBars.length===20){
  var nLit=Math.floor(D.prod*2);
  for(var i=0;i<20;i++){
    solarBars[i].setAttribute("opacity",i<nLit?"0.5":"0.14");
  }
}

// Battery SoC bars
var batBars=document.querySelectorAll("#topo-bat-bars rect");
if(batBars.length===20){
  var nBat=Math.floor(D.soc/5);
  var batCol=D.soc>90?"#5794F2":D.soc>=30?"#73BF69":D.soc>=20?"#FF9830":D.soc>=10?"#FF6B3D":"#F2495C";
  var batG=document.getElementById("topo-bat-bars");
  if(batG)batG.setAttribute("fill",batCol);
  for(var i=0;i<20;i++){
    batBars[i].setAttribute("opacity",i<nBat?"0.4":"0.14");
  }
}

// House consumption bars
var houseBars=document.querySelectorAll("#topo-house-bars rect");
if(houseBars.length===20){
  var nH=Math.floor(D.cons*2);
  for(var i=0;i<20;i++){
    houseBars[i].setAttribute("opacity",i<nH?"0.5":"0.14");
  }
}

// Wallbox bars
var wbBars=document.querySelectorAll("#topo-wb-bars rect");
if(wbBars.length===20){
  var nW=Math.floor(D.charge*2);
  for(var i=0;i<20;i++){
    wbBars[i].setAttribute("opacity",i<nW?"0.5":"0.14");
  }
}

// Battery SoC text color
var socEl=document.getElementById("topo-bat-soc");
if(socEl){
  var sColor=D.soc>90?"#5794F2":D.soc>=30?"#73BF69":D.soc>=20?"#FF9830":D.soc>=10?"#FF6B3D":"#F2495C";
  socEl.setAttribute("fill",sColor);
}

// Grid diverging bars
var gridBars=document.querySelectorAll("#topo-grid-bars rect");
if(gridBars.length===20){
  var mKw=D.meter;
  if(mKw>0.1){
    var nExp=Math.min(Math.floor(mKw),10);
    for(var i=0;i<10;i++){gridBars[9-i].setAttribute("opacity",i<nExp?"0.5":"0.14");}
    for(var i=10;i<20;i++){gridBars[i].setAttribute("opacity","0.14");}
  }else if(mKw<-0.1){
    var nImp=Math.min(Math.floor(Math.abs(mKw)),10);
    for(var i=0;i<10;i++){gridBars[i].setAttribute("opacity","0.14");}
    for(var i=0;i<nImp;i++){gridBars[10+i].setAttribute("opacity","0.5");}
  }
}"""

PANEL_80_HELPERS = (
    'handlebars.registerHelper("lt", function(a, b) '
    '{ return parseFloat(a) < parseFloat(b); });\n'
    'handlebars.registerHelper("gt", function(a, b) '
    '{ return parseFloat(a) > parseFloat(b); });\n'
    'handlebars.registerHelper("gte", function(a, b) '
    '{ return parseFloat(a) >= parseFloat(b); });\n'
    'handlebars.registerHelper("abs", function(a) '
    '{ return Math.abs(parseFloat(a)); });'
)


def build_panel_80():
    targets = [
        flux_target(PANEL_80_QUERY_A, "A"),
        flux_target(PANEL_80_QUERY_B, "B"),
    ]
    return business_text_panel(
        panel_id=80,
        grid_pos={"x": 0, "y": 12, "w": 15, "h": 7},
        targets=targets,
        content=PANEL_80_CONTENT,
        helpers=PANEL_80_HELPERS,
        after_render=PANEL_80_AFTER_RENDER,
    )


# ===================================================================
# PANEL 81 -- Energy Chart (timeseries)
# ===================================================================

def build_panel_81():
    targets = [
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "FVE" and '
            'r._field == "power" and r.string == "all")\n'
            "  |> map(fn: (r) => ({r with _value: r._value / 1000.0}))\n"
            "  |> aggregateWindow(every: v.windowPeriod, fn: max)",
            "A",
        ),
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "FVE" and '
            'r._field == "consumption")\n'
            "  |> map(fn: (r) => ({r with _value: r._value / 1000.0}))\n"
            "  |> aggregateWindow(every: v.windowPeriod, fn: max)",
            "B",
        ),
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "FVE" and '
            'r._field == "battery_load")\n'
            "  |> map(fn: (r) => ({r with _value: r._value / 1000.0}))\n"
            "  |> aggregateWindow(every: v.windowPeriod, fn: max)",
            "C",
        ),
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "FVE" and '
            'r._field == "bojlery" and r.pretoky == "pretoky")\n'
            "  |> map(fn: (r) => ({r with _value: r._value / 1000.0}))\n"
            "  |> aggregateWindow(every: v.windowPeriod, fn: max)",
            "D",
        ),
    ]
    overrides = [
        {
            "matcher": {"id": "byFrameRefID", "options": "A"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#5794F2", "mode": "fixed"}},
                {"id": "displayName", "value": "Solar"},
            ],
        },
        {
            "matcher": {"id": "byFrameRefID", "options": "B"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#73bf69", "mode": "fixed"}},
                {"id": "displayName", "value": "House"},
            ],
        },
        {
            "matcher": {"id": "byFrameRefID", "options": "C"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#FADE2A", "mode": "fixed"}},
                {"id": "displayName", "value": "Battery"},
            ],
        },
        {
            "matcher": {"id": "byFrameRefID", "options": "D"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#FF9830", "mode": "fixed"}},
                {"id": "displayName", "value": "Bojlery"},
            ],
        },
    ]
    panel = timeseries_panel(
        panel_id=81,
        grid_pos={"x": 0, "y": 19, "w": 15, "h": 13},
        targets=targets,
        overrides=overrides,
    )
    # Override time range: today midnight → now (independent of dashboard range)
    panel["timeFrom"] = "now/d"
    return panel


# ===================================================================
# PANEL 82 -- Energy Stats
# ===================================================================

PANEL_82_CONTENT = r"""<style>
.estat{font-family:'Inter','Helvetica Neue',Arial,sans-serif;display:flex;background:#111217;height:100%;overflow:hidden}
.estat .s{flex:1;padding:8px 14px;border-right:1px solid rgba(255,255,255,0.06);display:flex;flex-direction:column;gap:3px;justify-content:center}
.estat .s:last-child{border-right:none}
.estat .lab{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8e8e8e;font-weight:700}
.estat .val{font-size:28px;font-weight:700;line-height:1}
.estat .val .unit{font-size:12px;color:#8e8e8e;margin-left:3px;font-weight:400}
.estat .s-diverge{flex:2;padding:8px 14px 10px;gap:4px}
.s-diverge .dv-head{display:flex;justify-content:space-between;align-items:baseline}
.s-diverge .dv-delta{font-size:18px;font-weight:800;line-height:1}
.s-diverge .dv-delta .unit{font-size:11px;color:#8e8e8e;font-weight:500;margin-left:2px}
.s-diverge .dv-row{display:grid;grid-template-columns:50px 1fr 50px;align-items:center;column-gap:8px}
.s-diverge .dv-cons,.s-diverge .dv-prod{font-size:24px;font-weight:700;line-height:1}
.s-diverge .dv-cons{text-align:right}
.s-diverge .dv-prod{text-align:left}
.s-diverge .dv-bar{display:grid;grid-template-columns:1fr 1fr;height:8px;position:relative}
.s-diverge .dv-bar::before{content:'';position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:#5a5f66;transform:translateX(-50%);z-index:1}
.s-diverge .dv-half{display:flex;height:100%;overflow:hidden}
.s-diverge .dv-half-l{justify-content:flex-end}
.s-diverge .dv-half-r{justify-content:flex-start}
.s-diverge .dv-fill{height:100%}
.s-diverge .dv-fill-cons{background:#f2495c;border-radius:3px 0 0 3px}
.s-diverge .dv-fill-prod{background:#73bf69;border-radius:0 3px 3px 0}
</style>
<div class="estat" id="estat-root"
  data-d-cons="{{d_cons}}" data-d-gen="{{d_gen}}"
  data-m-cons="{{m_cons}}" data-m-gen="{{m_gen}}"
  data-self-suf="{{self_suf}}" data-vb-pct="{{vb_pct}}">
  <div class="s s-diverge">
    <div class="dv-head">
      <span class="lab">Today</span>
      <span class="dv-delta" id="estat-d-delta"></span>
    </div>
    <div class="dv-row">
      <span class="dv-cons" style="color:#f2495c">{{d_cons}}</span>
      <div class="dv-bar">
        <div class="dv-half dv-half-l"><div class="dv-fill dv-fill-cons" id="estat-d-cons-bar"></div></div>
        <div class="dv-half dv-half-r"><div class="dv-fill dv-fill-prod" id="estat-d-prod-bar"></div></div>
      </div>
      <span class="dv-prod" style="color:#73bf69">{{d_gen}}</span>
    </div>
  </div>
  <div class="s s-diverge">
    <div class="dv-head">
      <span class="lab">Month</span>
      <span class="dv-delta" id="estat-m-delta"></span>
    </div>
    <div class="dv-row">
      <span class="dv-cons" style="color:#f2495c">{{m_cons}}</span>
      <div class="dv-bar">
        <div class="dv-half dv-half-l"><div class="dv-fill dv-fill-cons" id="estat-m-cons-bar"></div></div>
        <div class="dv-half dv-half-r"><div class="dv-fill dv-fill-prod" id="estat-m-prod-bar"></div></div>
      </div>
      <span class="dv-prod" style="color:#73bf69">{{m_gen}}</span>
    </div>
  </div>
  <div class="s"><span class="lab">Self-suff.</span><span class="val" style="color:#73bf69">{{self_suf}}<span class="unit">%</span></span></div>
  <div class="s"><span class="lab">Virt. batt.</span><span class="val" style="color:#FADE2A">{{vb_pct}}<span class="unit">%</span></span></div>
</div>"""

PANEL_82_AFTER_RENDER = r"""var root=document.getElementById("estat-root");
if(!root)return;
var dc=parseFloat(root.dataset.dCons)||0,dg=parseFloat(root.dataset.dGen)||0;
var mc=parseFloat(root.dataset.mCons)||0,mg=parseFloat(root.dataset.mGen)||0;

function setBars(consId,prodId,deltaId,c,g){
  var mx=Math.max(c,g,0.1);
  var cb=document.getElementById(consId),gb=document.getElementById(prodId);
  if(cb)cb.style.width=(c/mx*100)+"%";
  if(gb)gb.style.width=(g/mx*100)+"%";
  var dd=document.getElementById(deltaId);
  if(dd){
    var delta=g-c;
    var sign=delta>=0?"+":"";
    var color=delta>=0?"#73bf69":"#f2495c";
    dd.innerHTML='<span style="color:'+color+'">'+sign+delta.toFixed(1)+'<span class="unit"> kWh</span></span>';
  }
}
setBars("estat-d-cons-bar","estat-d-prod-bar","estat-d-delta",dc,dg);
setBars("estat-m-cons-bar","estat-m-prod-bar","estat-m-delta",mc,mg);"""


def build_panel_82():
    # Reuse the same query as panel 80 (refId A)
    targets = [flux_target(PANEL_80_QUERY_A, "A")]
    return business_text_panel(
        panel_id=82,
        grid_pos={"x": 0, "y": 32, "w": 15, "h": 5},
        targets=targets,
        content=PANEL_82_CONTENT,
        after_render=PANEL_82_AFTER_RENDER,
    )


# ===================================================================
# PANEL 83 -- Heat Tiles
# ===================================================================

PANEL_83_QUERY = r"""import "math"
import "array"

// -- Krb (fireplace) --
krb_w_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "krb" and r._field == "apower")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

krb_t_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "krb" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// Krb trend (delta over 1h)
krb_now = from(bucket: "default")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "krb" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

krb_1h = from(bucket: "default")
  |> range(start: -2h, stop: -50m)
  |> filter(fn: (r) => r._measurement == "krb" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

krb_trend_val = if exists krb_now._value and exists krb_1h._value
  then math.round(x: (krb_now._value - krb_1h._value) * 10.0) / 10.0
  else 0.0

// -- COP --
cop_now = from(bucket: "default")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "Estia" and r._field == "cop_24h")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

cop_3h_ago = from(bucket: "default")
  |> range(start: -6h, stop: -2h)
  |> filter(fn: (r) => r._measurement == "Estia" and r._field == "cop_24h")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

cop_delta = if exists cop_now._value and exists cop_3h_ago._value
  then math.round(x: (cop_now._value - cop_3h_ago._value) * 100.0) / 100.0
  else 0.0

// -- Compressor on (float 0/1) --
comp_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
comp_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "compressor_on")
  |> last()
  |> keep(columns: ["_time", "_value"])
comp_rec = union(tables: [comp_default, comp_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Coil on (float 0/1) --
coil_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
coil_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "coil_on")
  |> last()
  |> keep(columns: ["_time", "_value"])
coil_rec = union(tables: [coil_default, coil_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Estia temps --
out_temp_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
out_temp_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "out_temp")
  |> last()
  |> keep(columns: ["_time", "_value"])
out_temp_rec = union(tables: [out_temp_default, out_temp_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

in_temp_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
in_temp_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "in_temp")
  |> last()
  |> keep(columns: ["_time", "_value"])
in_temp_rec = union(tables: [in_temp_default, in_temp_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

array.from(rows: [{
  krb_w: if exists krb_w_raw._value then math.round(x: float(v: krb_w_raw._value)) else 0.0,
  krb_t: if exists krb_t_raw._value then math.round(x: float(v: krb_t_raw._value) * 10.0) / 10.0 else 0.0,
  krb_trend: krb_trend_val,
  cop: if exists cop_now._value then math.round(x: float(v: cop_now._value) * 100.0) / 100.0 else 0.0,
  cop_3h: cop_delta,
  compressor: if exists comp_rec._value then comp_rec._value else 0.0,
  coil: if exists coil_rec._value then coil_rec._value else 0.0,
  out_temp: if exists out_temp_rec._value then math.round(x: float(v: out_temp_rec._value) * 10.0) / 10.0 else 0.0,
  in_temp: if exists in_temp_rec._value then math.round(x: float(v: in_temp_rec._value) * 10.0) / 10.0 else 0.0,
}])"""

PANEL_83_CONTENT = r"""<style>
.htiles{font-family:'Inter','Helvetica Neue',Arial,sans-serif;display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:8px;padding:8px 10px;height:100%;min-height:0}
.htile{background:#1a1d22;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 14px;display:flex;flex-direction:column;gap:4px;justify-content:center}
.htile .lab{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8e8e8e;font-weight:700}
.htile .big{font-size:36px;font-weight:700;line-height:1}
.htile .sub{font-size:12px;color:#8e8e8e}
.htile .sub b{color:#d8d9da;font-weight:700}
.htile-head{display:flex;align-items:center;justify-content:space-between}
.pill-sm{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border:1px solid transparent}
.pill-sm-comp{background:rgba(115,191,105,.14);color:#73bf69;border-color:rgba(115,191,105,.28)}
.pill-sm-coil{background:rgba(242,73,92,.14);color:#f2495c;border-color:rgba(242,73,92,.28)}
.pill-sm-off{background:rgba(142,142,142,.10);color:#6a6a6a;border-color:rgba(142,142,142,.18)}
.pill-sm .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
.htile-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
</style>
<div class="htiles">
  <div class="htile">
    <div class="htile-head">
      <span class="lab">Krb</span>
      {{#if (gt krb_w 20)}}<span class="pill-sm pill-sm-on"><span class="dot"></span>On</span>{{else}}<span class="pill-sm pill-sm-off"><span class="dot"></span>Off</span>{{/if}}
    </div>
    <div class="htile-row">
      <span class="big" style="color:{{#if (gt krb_t 60)}}#f2495c{{else if (gt krb_t 40)}}#FF9830{{else if (gt krb_t 15)}}#73bf69{{else}}#5794F2{{/if}}">{{krb_t}}&deg;</span>
      <span style="font-size:20px;font-weight:700;line-height:1;color:#5794F2">{{#if (gt krb_trend 0)}}&uarr;{{else if (lt krb_trend 0)}}&darr;{{else}}&mdash;{{/if}} {{krb_trend}}<span style="font-size:12px;font-weight:600;color:#8e8e8e"> &deg;/h</span></span>
    </div>
  </div>
  <div class="htile">
    <span class="lab">COP &middot; 24h</span>
    <div class="htile-row">
      <span class="big" style="color:{{#if (gt cop 3.5)}}#73bf69{{else if (gt cop 2.5)}}#FADE2A{{else}}#f2495c{{/if}}">{{cop}}</span>
      <span style="font-size:16px;font-weight:700;line-height:1;color:{{#if (gt cop_3h 0)}}#73bf69{{else if (lt cop_3h 0)}}#f2495c{{else}}#8e8e8e{{/if}}">{{#if (gt cop_3h 0)}}&uarr;{{else if (lt cop_3h 0)}}&darr;{{else}}&mdash;{{/if}} {{cop_3h}}<span style="font-size:11px;font-weight:600;color:#8e8e8e;margin-left:3px">3h</span></span>
    </div>
  </div>
  <div class="htile">
    <div class="htile-head">
      <span class="lab">Heat Pump</span>
      {{#if (gt compressor 0)}}<span class="pill-sm pill-sm-comp"><span class="dot"></span>Compressor</span>{{else if (gt coil 0)}}<span class="pill-sm pill-sm-coil"><span class="dot"></span>Heat coil</span>{{else}}<span class="pill-sm pill-sm-off"><span class="dot"></span>Off</span>{{/if}}
    </div>
    <div class="htile-row">
      <span style="font-size:24px;font-weight:700;line-height:1;color:#FADE2A">{{out_temp}}&deg;<span style="font-size:11px;font-weight:600;color:#8e8e8e;margin-left:3px">out</span></span>
      <span style="font-size:14px;color:#555;font-weight:500">/</span>
      <span style="font-size:24px;font-weight:700;line-height:1;color:#5794F2">{{in_temp}}&deg;<span style="font-size:11px;font-weight:600;color:#8e8e8e;margin-left:3px">in</span></span>
    </div>
  </div>
</div>"""


def build_panel_83():
    targets = [flux_target(PANEL_83_QUERY, "A")]
    return business_text_panel(
        panel_id=83,
        grid_pos={"x": 15, "y": 12, "w": 9, "h": 5},
        targets=targets,
        content=PANEL_83_CONTENT,
        helpers=PANEL_80_HELPERS,  # same lt/gt/gte/abs helpers
    )


# ===================================================================
# PANEL 84 -- TC Chart (timeseries)
# ===================================================================

def build_panel_84():
    targets = [
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "estia" and '
            'r._field == "target_temp")\n'
            "  |> aggregateWindow(every: v.windowPeriod, fn: last)",
            "A",
        ),
        flux_target(
            'from(bucket: "default")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            '  |> filter(fn: (r) => r._measurement == "becka" and '
            'r._field == "tC")\n'
            "  |> aggregateWindow(every: v.windowPeriod, fn: last)",
            "B",
        ),
    ]
    overrides = [
        {
            "matcher": {"id": "byFrameRefID", "options": "A"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#73bf69", "mode": "fixed"}},
                {"id": "displayName", "value": "Target"},
            ],
        },
        {
            "matcher": {"id": "byFrameRefID", "options": "B"},
            "properties": [
                {"id": "color", "value": {"fixedColor": "#FADE2A", "mode": "fixed"}},
                {"id": "displayName", "value": "Water"},
            ],
        },
    ]
    return timeseries_panel(
        panel_id=84,
        grid_pos={"x": 15, "y": 17, "w": 9, "h": 5},
        targets=targets,
        overrides=overrides,
        line_width=3,
        fill_opacity=0,
        show_legend=False,
    )


# ===================================================================
# PANEL 85 -- Heat Stats
# ===================================================================

PANEL_85_QUERY = r"""import "math"
import "array"

// Target temp
target_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "estia" and r._field == "target_temp")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// Water (becka) temp
water_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "becka" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// Water trend (1h)
water_now = from(bucket: "default")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "becka" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

water_1h = from(bucket: "default")
  |> range(start: -2h, stop: -50m)
  |> filter(fn: (r) => r._measurement == "becka" and r._field == "tC")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

water_trend_val = if exists water_now._value and exists water_1h._value
  then math.round(x: (water_now._value - water_1h._value) * 10.0) / 10.0
  else 0.0

target_t = if exists target_raw._value then math.round(x: float(v: target_raw._value) * 10.0) / 10.0 else 0.0
water_t = if exists water_raw._value then math.round(x: float(v: water_raw._value) * 10.0) / 10.0 else 0.0
delta_t = math.round(x: (target_t - water_t) * 10.0) / 10.0

array.from(rows: [{
  target_t: target_t,
  water_t: water_t,
  delta_t: delta_t,
  water_trend: water_trend_val,
}])"""

PANEL_85_CONTENT = r"""<style>
.hstats{font-family:'Inter','Helvetica Neue',Arial,sans-serif;display:flex;background:#111217;height:100%;overflow:hidden}
.hstats .s{flex:1;padding:8px 14px;border-right:1px solid rgba(255,255,255,0.06);display:flex;flex-direction:column;gap:3px;justify-content:center}
.hstats .s:last-child{border-right:none}
.hstats .lab{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8e8e8e;font-weight:700}
.hstats .val{font-size:28px;font-weight:700;line-height:1}
.hstats .val .unit{font-size:12px;color:#8e8e8e;margin-left:3px;font-weight:400}
</style>
<div class="hstats">
  <div class="s"><span class="lab">Target</span><span class="val" style="color:#73bf69">{{target_t}}<span class="unit">&deg;C</span></span></div>
  <div class="s"><span class="lab">Water</span><span class="val" style="color:#FADE2A">{{water_t}}<span class="unit">&deg;C</span></span></div>
  <div class="s"><span class="lab">&Delta;</span><span class="val" style="color:#d8d9da">{{delta_t}}<span class="unit">K</span></span></div>
  <div class="s"><span class="lab">Trend 1h</span><span class="val" style="color:#5794F2">{{water_trend}}<span class="unit">K/h</span></span></div>
</div>"""


def build_panel_85():
    targets = [flux_target(PANEL_85_QUERY, "A")]
    return business_text_panel(
        panel_id=85,
        grid_pos={"x": 15, "y": 22, "w": 9, "h": 5},
        targets=targets,
        content=PANEL_85_CONTENT,
    )


# ===================================================================
# PANEL 86 -- Vehicles
# ===================================================================

PANEL_86_QUERY = r"""import "math"
import "array"

// -- Enyaq --
enyaq_soc_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "battery_level_enyaq")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

enyaq_range_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "electric_range_enyaq")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

enyaq_time_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
enyaq_time_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "charging_time_left_enyaq")
  |> last()
  |> keep(columns: ["_time", "_value"])
enyaq_time_rec = union(tables: [enyaq_time_default, enyaq_time_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- ID.3 --
vw_soc_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "battery_level_vw")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

vw_range_raw = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "electric_range_vw")
  |> last()
  |> findRecord(fn: (key) => true, idx: 0)

vw_time_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
vw_time_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "charging_time_left_vw")
  |> last()
  |> keep(columns: ["_time", "_value"])
vw_time_rec = union(tables: [vw_time_default, vw_time_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

// -- Shared wallbox --
charge_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
charge_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "charging_wallbox_power")
  |> last()
  |> keep(columns: ["_time", "_value"])
charge_rec = union(tables: [charge_default, charge_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

conn_default = array.from(rows: [{_time: 2000-01-01T00:00:00Z, _value: 0.0}])
conn_real = from(bucket: "default")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "Car" and r._field == "car_connected")
  |> last()
  |> keep(columns: ["_time", "_value"])
conn_rec = union(tables: [conn_default, conn_real])
  |> sort(columns: ["_time"]) |> last()
  |> findRecord(fn: (key) => true, idx: 0)

enyaq_soc = if exists enyaq_soc_raw._value then math.round(x: float(v: enyaq_soc_raw._value)) else 0.0
enyaq_range = if exists enyaq_range_raw._value then math.round(x: float(v: enyaq_range_raw._value)) else 0.0
enyaq_max = if enyaq_soc > 0.0 then math.round(x: enyaq_range / enyaq_soc * 100.0) else 0.0
enyaq_time = if exists enyaq_time_rec._value then math.round(x: float(v: enyaq_time_rec._value)) else 0.0

vw_soc = if exists vw_soc_raw._value then math.round(x: float(v: vw_soc_raw._value)) else 0.0
vw_range = if exists vw_range_raw._value then math.round(x: float(v: vw_range_raw._value)) else 0.0
vw_max = if vw_soc > 0.0 then math.round(x: vw_range / vw_soc * 100.0) else 0.0
vw_time = if exists vw_time_rec._value then math.round(x: float(v: vw_time_rec._value)) else 0.0

charge_w = if exists charge_rec._value then float(v: charge_rec._value) else 0.0
car_conn = if exists conn_rec._value then float(v: conn_rec._value) else 0.0

array.from(rows: [{
  enyaq_soc: enyaq_soc, enyaq_range: enyaq_range, enyaq_max: enyaq_max, enyaq_time: enyaq_time,
  vw_soc: vw_soc, vw_range: vw_range, vw_max: vw_max, vw_time: vw_time,
  charge_w: charge_w, car_conn: car_conn,
}])"""

PANEL_86_CONTENT = r"""<style>
.cars{font-family:'Inter','Helvetica Neue',Arial,sans-serif;display:grid;grid-template-columns:1fr;grid-auto-rows:1fr;gap:10px;padding:10px 14px 14px;height:100%;min-height:0}
.car-card{background:#1a1d22;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px 16px;display:flex;flex-direction:column;gap:8px;justify-content:center}
.car-row1{display:flex;align-items:center;gap:14px}
.car-name{font-size:28px;font-weight:700;min-width:80px;flex-shrink:0;white-space:nowrap;line-height:1;letter-spacing:-0.01em;color:#d8d9da}
.car-soc-bar{flex:1;height:14px;background:#0e1013;border-radius:7px;overflow:visible;position:relative}
.car-soc-bar .gradient{position:absolute;inset:0;border-radius:7px;background:linear-gradient(90deg,#f2495c 0%,#f2495c 10%,#FF6B3D 10%,#FF6B3D 20%,#FF9830 20%,#FF9830 30%,#73bf69 30%,#73bf69 90%,#5794F2 90%,#5794F2 100%)}
.car-soc-bar .cover{position:absolute;top:0;right:0;height:100%;background:#0e1013;border-radius:0 7px 7px 0}
.car-soc{font-size:22px;font-weight:700;min-width:60px;text-align:right;line-height:1;white-space:nowrap}
.car-row2{display:flex;align-items:baseline;gap:14px;font-size:18px;padding-left:94px}
.car-row2 .car-range{color:#d8d9da;font-weight:700;font-size:18px}
.car-row2 .car-maxrange{color:#8e8e8e}
.car-row2 .car-timeleft{color:#FF9830;font-weight:600}
.car-row2 .car-status{margin-left:auto}
.pill-car{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border:1px solid transparent}
.pill-car-disc{background:rgba(142,142,142,.10);color:#8e8e8e;border-color:rgba(142,142,142,.18)}
.pill-car-chg{background:rgba(255,152,48,.14);color:#FF9830;border-color:rgba(255,152,48,.28)}
.pill-car-conn{background:rgba(115,191,105,.14);color:#73bf69;border-color:rgba(115,191,105,.28)}
.pill-car .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
@keyframes car-pulse{0%,100%{opacity:1}50%{opacity:.4}}
.car-card.charging .car-soc-bar .gradient{animation:car-pulse 2s ease-in-out infinite}
</style>
<div class="cars" id="cars-root"
  data-enyaq-soc="{{enyaq_soc}}" data-enyaq-range="{{enyaq_range}}" data-enyaq-max="{{enyaq_max}}" data-enyaq-time="{{enyaq_time}}"
  data-vw-soc="{{vw_soc}}" data-vw-range="{{vw_range}}" data-vw-max="{{vw_max}}" data-vw-time="{{vw_time}}"
  data-charge-w="{{charge_w}}" data-car-conn="{{car_conn}}">

  <div class="car-card" id="car-enyaq">
    <div class="car-row1">
      <div class="car-name">Enyaq</div>
      <div class="car-soc-bar">
        <div class="gradient"></div>
        <div class="cover" id="enyaq-cover"></div>
      </div>
      <div class="car-soc" id="enyaq-soc-text">{{enyaq_soc}}%</div>
    </div>
    <div class="car-row2">
      <span class="car-range">{{enyaq_range}} km</span>
      <span class="car-maxrange">max {{enyaq_max}} km</span>
      <span class="car-timeleft" id="enyaq-time"></span>
      <span class="car-status" id="enyaq-status"></span>
    </div>
  </div>

  <div class="car-card" id="car-vw">
    <div class="car-row1">
      <div class="car-name">ID.3</div>
      <div class="car-soc-bar">
        <div class="gradient"></div>
        <div class="cover" id="vw-cover"></div>
      </div>
      <div class="car-soc" id="vw-soc-text">{{vw_soc}}%</div>
    </div>
    <div class="car-row2">
      <span class="car-range">{{vw_range}} km</span>
      <span class="car-maxrange">max {{vw_max}} km</span>
      <span class="car-timeleft" id="vw-time"></span>
      <span class="car-status" id="vw-status"></span>
    </div>
  </div>
</div>"""

PANEL_86_AFTER_RENDER = r"""var root=document.getElementById("cars-root");
if(!root)return;
var eSoc=parseFloat(root.dataset.enyaqSoc)||0;
var eTime=parseFloat(root.dataset.enyaqTime)||0;
var vSoc=parseFloat(root.dataset.vwSoc)||0;
var vTime=parseFloat(root.dataset.vwTime)||0;
var chargeW=parseFloat(root.dataset.chargeW)||0;
var conn=parseFloat(root.dataset.carConn)||0;

// SoC bar cover
var ec=document.getElementById("enyaq-cover");
if(ec)ec.style.width=(100-eSoc)+"%";
var vc=document.getElementById("vw-cover");
if(vc)vc.style.width=(100-vSoc)+"%";

// SoC text color
function socColor(s){return s>90?"#5794F2":s>=30?"#73bf69":s>=20?"#FF9830":s>=10?"#FF6B3D":"#f2495c";}
var esTxt=document.getElementById("enyaq-soc-text");
if(esTxt)esTxt.style.color=socColor(eSoc);
var vsTxt=document.getElementById("vw-soc-text");
if(vsTxt)vsTxt.style.color=socColor(vSoc);

// Status pills
var eStat=document.getElementById("enyaq-status");
var vStat=document.getElementById("vw-status");

// Determine which car is charging (if wallbox is active)
var enyaqCharging=conn>0&&chargeW>0.1&&eTime>0;
var vwCharging=conn>0&&chargeW>0.1&&vTime>0&&!enyaqCharging;

if(eStat){
  if(enyaqCharging){
    eStat.innerHTML='<span class="pill-car pill-car-chg"><span class="dot"></span>Charging</span>';
    var eCard=document.getElementById("car-enyaq");
    if(eCard)eCard.classList.add("charging");
  }else{
    eStat.innerHTML='<span class="pill-car pill-car-disc"><span class="dot"></span>Disconnected</span>';
  }
}
if(vStat){
  if(vwCharging){
    vStat.innerHTML='<span class="pill-car pill-car-chg"><span class="dot"></span>Charging</span>';
    var vCard=document.getElementById("car-vw");
    if(vCard)vCard.classList.add("charging");
  }else{
    vStat.innerHTML='<span class="pill-car pill-car-disc"><span class="dot"></span>Disconnected</span>';
  }
}

// Time left
var eTimeEl=document.getElementById("enyaq-time");
if(eTimeEl&&eTime>0)eTimeEl.textContent="~"+Math.round(eTime)+" min";
var vTimeEl=document.getElementById("vw-time");
if(vTimeEl&&vTime>0)vTimeEl.textContent="~"+Math.round(vTime)+" min";"""


def build_panel_86():
    targets = [flux_target(PANEL_86_QUERY, "A")]
    return business_text_panel(
        panel_id=86,
        grid_pos={"x": 15, "y": 27, "w": 9, "h": 10},
        targets=targets,
        content=PANEL_86_CONTENT,
        after_render=PANEL_86_AFTER_RENDER,
        helpers=PANEL_80_HELPERS,
    )


# ===================================================================
# Main: load, replace panels, write
# ===================================================================

def main():
    with open(DASHBOARD_PATH, "r") as f:
        data = json.load(f)

    existing_panels = data["dashboard"]["panels"]

    # Build new panels
    panels = [
        build_panel_70(existing_panels),   # Outdoor
        build_panel_67(existing_panels),   # Indoor
        build_panel_80(),                   # Energy Topology
        build_panel_81(),                   # Energy Chart
        build_panel_82(),                   # Energy Stats
        build_panel_83(),                   # Heat Tiles
        build_panel_84(),                   # TC Chart
        build_panel_85(),                   # Heat Stats
        build_panel_86(),                   # Vehicles
    ]

    # Replace panels
    data["dashboard"]["panels"] = panels

    # Ensure dashboard metadata is correct
    data["dashboard"]["uid"] = "q50mEhf7k"
    data["dashboard"]["title"] = "Prdikov"
    data["dashboard"]["refresh"] = "10s"
    data["dashboard"]["time"] = {"from": "now-3h", "to": "now"}

    # Write back
    with open(DASHBOARD_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Dashboard written to {DASHBOARD_PATH}")
    print(f"  Panels: {len(panels)}")
    for p in panels:
        gp = p["gridPos"]
        print(f"    ID {p['id']:3d}  {p['type'][:30]:30s}  "
              f"({gp['x']},{gp['y']}) {gp['w']}x{gp['h']}")


if __name__ == "__main__":
    main()
