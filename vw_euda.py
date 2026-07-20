"""VW ID.3 telemetry via the EU Data Act portal -> MQTT.

Standalone service replacing the (now dead) VW branch of skoda.py. It keeps a
sticky merged snapshot of the portal's flat key/value export and republishes
to the same `home/Car/*_vw` topics the dashboard and InfluxDB already consume.

The portal drops a new ZIP only ~every 15 min, so between drops the SoC is
*interpolated* forward from the last reading using charge power, elapsed time
(from the reading's own timestamp) and the battery capacity — and published
every minute so the dashboard tracks charging live. The service ticks once a
minute but only downloads a file when a new one is available.

The export has no range and no GPS, so range is approximated from SoC and
location is no longer published for the VW.
"""
import sys
import time
from datetime import datetime, timezone

sys.stdout.reconfigure(line_buffering=True)

from common import connect_mqtt, publishProperties  # noqa: E402
from config import skodaConfig, vwEudaConfig as cfg  # noqa: E402
from vw_euda_auth import ApiError, EudaClient  # noqa: E402

CHARGING_STATE = "CHARGE_STATE_CHARGING_HV_BATTERY"
# The export repeats car_captured_(utc_)time once per vehicle data domain and
# most are stale duplicates, so collapsing by field name grabs the wrong one.
# This is the stable `key` of the entry that anchors the battery/SoC reading.
CAPTURE_KEY = cfg.get("battery_capture_key")
# Fallback only, when the keyed entry is absent: the *freshest* of these wins
# (never the stale-biased last-seen duplicate).
CAPTURE_TIME_FIELDS = (
    "car_captured_utc_timestamp",
    "car_captured_time",
    "timestamp",
)
# Synthetic field the merge stashes the resolved capture time under, so it
# survives the collapse-by-name and is what the interpolation anchors to.
CAPTURE_FIELD = "__capture__"
# Preference order for the charge target: the user-set charge limit first,
# then the battery-care cap.
TARGET_FIELDS = (
    "settings.target_soc",
    "battery_care_mode.charge_bcam_threshold",
)


# --- pure helpers (unit-tested, no network/MQTT) -------------------------

def build_field_dict(payloads, into=None):
    """Merge export payloads (oldest->newest) into a sticky field dict.

    The 15-min ZIPs are deltas: a file may omit fields it hasn't seen change,
    so newest-last means the freshest value of every field wins. Pass an
    existing dict as `into` to merge incrementally across polls.

    NOTE: this merges strictly in the order given, so callers must pass
    payloads in capture-time order. The service uses `merge_capture_aware`
    instead, which is robust to the portal serving files out of order.
    """
    merged = dict(into) if into else {}
    for payload in payloads:
        for item in payload.get("Data", []):
            name = item.get("dataFieldName")
            if name is not None:
                merged[name] = item.get("value")
    return merged


def payload_capture(payload):
    """Authoritative capture time of a single export payload.

    Prefers the entry tagged with `CAPTURE_KEY` (the battery/SoC domain's own
    timestamp). If that key is absent, falls back to the *freshest* value
    among the generic capture fields — never the stale-biased last-seen one.
    """
    keyed = None
    freshest = None
    for item in payload.get("Data", []):
        if CAPTURE_KEY and item.get("key") == CAPTURE_KEY:
            keyed = parse_ts(item.get("value"))
        if item.get("dataFieldName") in CAPTURE_TIME_FIELDS:
            ts = parse_ts(item.get("value"))
            if ts and (freshest is None or ts > freshest):
                freshest = ts
    return keyed or freshest


def merge_capture_aware(state, payload):
    """Merge one payload into a per-field {name: (value, capture)} state.

    The portal serves files out of capture-time order and mixes full
    snapshots with tiny deltas, so a strict newest-file-wins merge can let a
    stale snapshot overwrite fresher fields (and poison the anchor timestamp
    the interpolation projects from). This keeps, per field, the value from
    the freshest-captured payload that carried it. A payload with no capture
    timestamp can only fill fields we don't have yet, never overwrite dated
    ones. The resolved capture time is stashed under CAPTURE_FIELD so it
    survives the collapse-by-name and anchors the interpolation.
    """
    cap = payload_capture(payload)
    items = list(payload.get("Data", []))
    if cap is not None:
        items.append({"dataFieldName": CAPTURE_FIELD, "value": cap.isoformat()})
    for item in items:
        name = item.get("dataFieldName")
        if name is None:
            continue
        val = item.get("value")
        prev = state.get(name)
        if prev is None:
            state[name] = (val, cap)
            continue
        prev_cap = prev[1]
        if cap is None:
            continue
        if prev_cap is None or cap >= prev_cap:
            state[name] = (val, cap)
    return state


def state_values(state):
    """Flatten a capture-aware state back to a plain {name: value} dict."""
    return {name: value for name, (value, _) in state.items()}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_ts(raw):
    """Parse an ISO-8601 timestamp (handles trailing 'Z' on Python 3.9)."""
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def capture_time(d):
    """The authoritative capture timestamp of a merged reading.

    Prefers the capture the merge already resolved (by CAPTURE_KEY, stashed
    under CAPTURE_FIELD); falls back to the generic fields for plain dicts
    that never went through the capture-aware merge (e.g. a single payload).
    """
    dt = parse_ts(d.get(CAPTURE_FIELD))
    if dt:
        return dt
    for field in CAPTURE_TIME_FIELDS:
        dt = parse_ts(d.get(field))
        if dt:
            return dt
    return None


def soc_value(d):
    """SoC as float %, preferring the validated HV battery level."""
    if d.get("battery_level_HV.state") == "VALID":
        soc = _to_float(d.get("battery_level_HV.value"))
        if soc is not None:
            return soc
    return _to_float(d.get("battery_state_report.soc"))


def parse_target(d):
    """Charge target %, preferring the user-set limit over the care cap."""
    for field in TARGET_FIELDS:
        v = _to_float(d.get(field))
        if v is not None:
            return int(v)
    return None


def parse_range(d):
    """Electric range in km, reported by the portal in the bare 'value' key."""
    v = _to_float(d.get("value"))
    return int(round(v)) if v is not None else None


def is_charging(d):
    return d.get("charging_state_report.current_charge_state") == CHARGING_STATE


def is_plugged(d):
    """Plug connected: charging, or drawing external power (inferred)."""
    if is_charging(d):
        return True
    power = _to_float(d.get("battery_state_report.charge_power"))
    return power is not None and power > 0


def charging_minutes_left(d):
    """Remaining charge time in minutes as reported (0 when not charging)."""
    if not is_charging(d):
        return 0
    raw = d.get("battery_state_report.remaining_charging_time_complete")
    if not raw:
        return 0
    try:
        return int(round(float(str(raw).strip().rstrip("s")) / 60.0))
    except ValueError:
        return 0


def interpolate(d, now, capacity_kwh, efficiency, max_projection_min=None):
    """Map a merged field dict to {mqtt_field_suffix: value} at time `now`.

    When charging, SoC (and range, remaining time) is projected forward from
    the reading's capture time so values stay live between portal drops. Range
    starts from the portal's own reported value and is scaled in lockstep with
    the interpolated SoC. Only includes fields we have data for, so a partial
    snapshot never overwrites a good value.

    Projection is only trustworthy for a short window after capture. The
    portal frequently lags hours, so `max_projection_min` caps how far a
    reading may be extrapolated; past it we publish the raw last reading
    rather than inventing charge that may never have happened.
    """
    out = {}
    soc = soc_value(d)
    charging = is_charging(d)
    power = _to_float(d.get("battery_state_report.charge_power"))
    target = parse_target(d)
    captured = capture_time(d)
    elapsed_min = None
    if captured is not None:
        elapsed_min = max(0.0, (now - captured).total_seconds() / 60.0)

    fresh = (elapsed_min is not None
             and (max_projection_min is None
                  or elapsed_min <= max_projection_min))

    soc_live = soc
    if (soc is not None and charging and power and power > 0 and fresh):
        added = power * (elapsed_min / 60.0) / capacity_kwh * 100.0 * efficiency
        soc_live = soc + added
        limit = float(target) if target is not None else 100.0
        soc_live = min(soc_live, limit, 100.0)

    if soc_live is not None:
        out["battery_level_vw"] = int(round(soc_live))

    range_km = parse_range(d)
    if range_km is not None:
        # Extrapolate range over time in lockstep with the interpolated SoC
        # (a no-op unless SoC was projected, since then soc_live == soc).
        if soc and soc > 0 and soc_live is not None:
            range_km = int(round(range_km * soc_live / soc))
        out["electric_range_vw"] = range_km

    if charging:
        base = charging_minutes_left(d)
        if fresh:
            out["charging_time_left_vw"] = max(0, int(round(base - elapsed_min)))
        else:
            out["charging_time_left_vw"] = base
    elif (d.get("charging_state_report.current_charge_state") is not None
          or power is not None):
        out["charging_time_left_vw"] = 0

    if (d.get("charging_state_report.current_charge_state") is not None
            or power is not None):
        out["plug_connected_vw"] = int(is_plugged(d))
    if power is not None:
        out["charge_power_vw"] = power
    if target is not None:
        out["target_soc_vw"] = target
    # Car-side capture time (the portal's, not our fetch time) as epoch
    # seconds, so the dashboard can show how stale the reading is — the
    # portal routinely lags hours behind real time.
    if captured is not None:
        out["captured_vw"] = captured.timestamp()

    return out


# --- service -------------------------------------------------------------

def _newest_first_sorted(files):
    """Return files oldest->newest by filename (YYYYMMDDHHMMSS prefix)."""
    return sorted(files, key=lambda f: f.get("name", ""))


def publish_readings(client, readings):
    for suffix, value in readings.items():
        client.publish(f"home/Car/{suffix}", value, qos=2,
                       properties=publishProperties).wait_for_publish()


def main():
    client = connect_mqtt("vw_euda")
    client.loop_start()
    vin = skodaConfig["vin_vw"]
    euda = EudaClient()
    print("[vw_euda] Started")

    ident = None
    state = {}          # capture-aware {name: (value, capture)} anchor
    last_file = None
    try:
        while True:
            # 1. Retrieve new data only when a newer file is available.
            try:
                if ident is None:
                    ident = euda.get_identifier(vin)
                files = _newest_first_sorted(euda.list_datasets(vin, ident))
                if files and files[-1]["name"] != last_file:
                    if last_file is None:
                        new = files[-cfg["merge_files"]:]
                    else:
                        new = [f for f in files if f["name"] > last_file]
                    for f in new:
                        merge_capture_aware(
                            state, euda.download_dataset(vin, ident, f["name"]))
                    last_file = files[-1]["name"]
                    d = state_values(state)
                    print(f"[vw_euda] New data {last_file}: "
                          f"SOC={soc_value(d)}%, "
                          f"captured={capture_time(d)}, "
                          f"charging={is_charging(d)}, "
                          f"power={d.get('battery_state_report.charge_power')}"
                          f"kW, target={parse_target(d)}")
            except ApiError as e:
                print(f"[vw_euda] API error: {str(e)[:200]}")
                ident = None   # force re-resolving the data-request identifier
            except Exception as e:
                print(f"[vw_euda] Fetch error: {str(e)[:200]}")

            # 2. Publish the (interpolated) readings every tick.
            if state:
                try:
                    readings = interpolate(
                        state_values(state), datetime.now(timezone.utc),
                        cfg["capacity_kwh"], cfg["charge_efficiency"],
                        cfg["max_projection_min"])
                    publish_readings(client, readings)
                    print(f"[vw_euda] Published: "
                          f"SOC={readings.get('battery_level_vw')}%, "
                          f"range={readings.get('electric_range_vw')}km, "
                          f"plug={readings.get('plug_connected_vw')}, "
                          f"time_left={readings.get('charging_time_left_vw')}min, "
                          f"target={readings.get('target_soc_vw')}, "
                          f"power={readings.get('charge_power_vw')}kW")
                except Exception as e:
                    print(f"[vw_euda] Publish error: {str(e)[:200]}")

            time.sleep(cfg["poll_interval"])
    finally:
        client.loop_stop()
        print("[vw_euda] Disconnecting")


if __name__ == "__main__":
    main()
