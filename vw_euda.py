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
# Preference order for "when was this reading captured" (all near-identical;
# the UTC capture timestamp is the most reliable anchor).
CAPTURE_TIME_FIELDS = (
    "car_captured_utc_timestamp",
    "timestamp",
    "car_captured_time",
)
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
    """
    merged = dict(into) if into else {}
    for payload in payloads:
        for item in payload.get("Data", []):
            name = item.get("dataFieldName")
            if name is not None:
                merged[name] = item.get("value")
    return merged


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
    """The freshest reliable capture timestamp in the reading."""
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


def interpolate(d, now, capacity_kwh, efficiency, km_per_soc):
    """Map a merged field dict to {mqtt_field_suffix: value} at time `now`.

    When charging, SoC (and hence range, remaining time) is projected forward
    from the reading's capture time so values stay live between portal drops.
    Only includes fields we have data for, so a partial snapshot never
    overwrites a good value with None.
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

    soc_live = soc
    if (soc is not None and charging and power and power > 0
            and elapsed_min is not None):
        added = power * (elapsed_min / 60.0) / capacity_kwh * 100.0 * efficiency
        soc_live = soc + added
        limit = float(target) if target is not None else 100.0
        soc_live = min(soc_live, limit, 100.0)

    if soc_live is not None:
        out["battery_level_vw"] = int(round(soc_live))
        out["electric_range_vw"] = int(soc_live * km_per_soc)

    if charging:
        base = charging_minutes_left(d)
        if elapsed_min is not None:
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
    state = {}          # sticky merged field dict (the interpolation anchor)
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
                    payloads = [euda.download_dataset(vin, ident, f["name"])
                                for f in new]
                    state = build_field_dict(payloads, into=state)
                    last_file = files[-1]["name"]
                    print(f"[vw_euda] New data {last_file}: "
                          f"SOC={soc_value(state)}%, "
                          f"charging={is_charging(state)}, "
                          f"power={state.get('battery_state_report.charge_power')}"
                          f"kW, target={parse_target(state)}")
            except ApiError as e:
                print(f"[vw_euda] API error: {str(e)[:200]}")
                ident = None   # force re-resolving the data-request identifier
            except Exception as e:
                print(f"[vw_euda] Fetch error: {str(e)[:200]}")

            # 2. Publish the (interpolated) readings every tick.
            if state:
                try:
                    readings = interpolate(
                        state, datetime.now(timezone.utc),
                        cfg["capacity_kwh"], cfg["charge_efficiency"],
                        cfg["km_per_soc"])
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
