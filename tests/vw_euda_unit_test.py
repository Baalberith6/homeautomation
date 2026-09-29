import inspect
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vw_euda  # noqa: E402


def _payload(fields):
    """Build an export payload from a {dataFieldName: value} dict."""
    return {"Data": [{"key": name, "dataFieldName": name, "value": val}
                     for name, val in fields.items()]}


def _raw(items):
    """Build a payload from explicit (key, dataFieldName, value) triples."""
    return {"Data": [{"key": k, "dataFieldName": n, "value": v}
                     for k, n, v in items]}


CAPTURE = "2026-07-07T12:00:00Z"

# The sample the portal returned while charging (subset of real fields).
SAMPLE = _payload({
    "battery_level_HV.value": "42.0",
    "battery_level_HV.state": "VALID",
    "battery_state_report.soc": "42",
    "battery_care_mode.charge_bcam_threshold": "80",
    "battery_state_report.remaining_charging_time_complete": "10500s",
    "battery_state_report.charge_power": "8.5",
    "charging_state_report.current_charge_state":
        "CHARGE_STATE_CHARGING_HV_BATTERY",
    "car_captured_utc_timestamp": CAPTURE,
    "value": "208",   # electric range in km, reported by the portal
})


SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "vw_euda_snapshot_2026-09-28.json")


class TestBuildFieldDict(unittest.TestCase):
    def test_newest_wins_on_merge(self):
        old = _payload({"battery_level_HV.value": "20.0"})
        new = _payload({"battery_level_HV.value": "42.0"})
        d = vw_euda.build_field_dict([old, new])
        self.assertEqual(d["battery_level_HV.value"], "42.0")

    def test_incremental_merge_keeps_prior(self):
        state = vw_euda.build_field_dict(
            [_payload({"battery_level_HV.value": "42.0",
                       "battery_level_HV.state": "VALID"})])
        # a later delta omitting SoC must not drop it
        state = vw_euda.build_field_dict(
            [_payload({"battery_state_report.charge_power": "8.5"})],
            into=state)
        self.assertEqual(state["battery_level_HV.value"], "42.0")
        self.assertEqual(state["battery_state_report.charge_power"], "8.5")


class TestParseHelpers(unittest.TestCase):
    def test_soc_prefers_valid_hv(self):
        self.assertEqual(vw_euda.soc_value(vw_euda.build_field_dict([SAMPLE])),
                         42.0)

    def test_soc_falls_back_when_invalid(self):
        d = {"battery_level_HV.value": "99.0",
             "battery_level_HV.state": "INVALID",
             "battery_state_report.soc": "45"}
        self.assertEqual(vw_euda.soc_value(d), 45.0)

    def test_target_prefers_settings(self):
        d = {"settings.target_soc": "60",
             "battery_care_mode.charge_bcam_threshold": "80"}
        self.assertEqual(vw_euda.parse_target(d), 60)

    def test_target_falls_back_to_bcam(self):
        d = {"battery_care_mode.charge_bcam_threshold": "80"}
        self.assertEqual(vw_euda.parse_target(d), 80)

    def test_parse_ts_handles_z(self):
        dt = vw_euda.parse_ts("2026-07-07T12:00:00Z")
        self.assertEqual(dt, datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc))

    def test_capture_time_prefers_utc_field(self):
        d = {"car_captured_time": "2026-07-07T11:39:03Z",
             "car_captured_utc_timestamp": "2026-07-07T12:00:00Z"}
        self.assertEqual(vw_euda.capture_time(d),
                         datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc))


class TestChargingHelpers(unittest.TestCase):
    def test_is_charging(self):
        self.assertTrue(vw_euda.is_charging(vw_euda.build_field_dict([SAMPLE])))

    def test_plugged_when_power_positive(self):
        d = {"charging_state_report.current_charge_state":
             "CHARGE_STATE_NOT_CHARGING",
             "battery_state_report.charge_power": "3.7"}
        self.assertTrue(vw_euda.is_plugged(d))

    def test_not_plugged(self):
        d = {"charging_state_report.current_charge_state":
             "CHARGE_STATE_NOT_CHARGING",
             "battery_state_report.charge_power": "0.0"}
        self.assertFalse(vw_euda.is_plugged(d))

    def test_minutes_left_zero_when_idle(self):
        d = {"charging_state_report.current_charge_state":
             "CHARGE_STATE_NOT_CHARGING",
             "battery_state_report.remaining_charging_time_complete": "600s"}
        self.assertEqual(vw_euda.charging_minutes_left(d), 0)


class TestCaptureKey(unittest.TestCase):
    def test_prefers_keyed_entry_over_stale_duplicates(self):
        # The export repeats car_captured_* per domain; most are stale. The
        # keyed entry must win over the last-seen duplicate.
        p = _raw([
            ("k1", "car_captured_utc_timestamp", "2026-07-08T06:52:20Z"),
            ("k2", "car_captured_utc_timestamp", "2026-07-08T06:52:21Z"),
            (vw_euda.CAPTURE_KEY, "car_captured_time", "2026-07-08T15:39:07Z"),
            ("k3", "car_captured_utc_timestamp", "2026-07-08T06:52:20Z"),
        ])
        self.assertEqual(vw_euda.payload_capture(p),
                         datetime(2026, 7, 8, 15, 39, 7, tzinfo=timezone.utc))

    def test_falls_back_to_freshest_not_last_seen(self):
        # keyed entry absent -> freshest generic value wins (not the last one)
        p = _raw([
            ("k1", "car_captured_utc_timestamp", "2026-07-08T15:01:22Z"),
            ("k2", "car_captured_utc_timestamp", "2026-07-08T06:52:20Z"),
        ])
        self.assertEqual(vw_euda.payload_capture(p),
                         datetime(2026, 7, 8, 15, 1, 22, tzinfo=timezone.utc))


class TestMergeCaptureAware(unittest.TestCase):
    def test_out_of_order_file_does_not_regress(self):
        state = {}
        fresh = _raw([
            (vw_euda.CAPTURE_KEY, "car_captured_time", "2026-07-08T15:39:07Z"),
            ("b", "battery_level_HV.value", "45.0"),
            ("s", "battery_level_HV.state", "VALID"),
        ])
        stale = _raw([
            (vw_euda.CAPTURE_KEY, "car_captured_time", "2026-07-08T06:52:00Z"),
            ("b", "battery_level_HV.value", "43.0"),
            ("s", "battery_level_HV.state", "VALID"),
        ])
        vw_euda.merge_capture_aware(state, fresh)
        vw_euda.merge_capture_aware(state, stale)   # later download, older data
        d = vw_euda.state_values(state)
        self.assertEqual(vw_euda.soc_value(d), 45.0)
        self.assertEqual(vw_euda.capture_time(d),
                         datetime(2026, 7, 8, 15, 39, 7, tzinfo=timezone.utc))

    def test_delta_fills_gaps_without_dropping_prior(self):
        state = {}
        vw_euda.merge_capture_aware(state, _raw([
            (vw_euda.CAPTURE_KEY, "car_captured_time", "2026-07-08T15:00:00Z"),
            ("b", "battery_level_HV.value", "50.0"),
            ("s", "battery_level_HV.state", "VALID"),
        ]))
        vw_euda.merge_capture_aware(state, _raw([
            (vw_euda.CAPTURE_KEY, "car_captured_time", "2026-07-08T15:15:00Z"),
            ("p", "battery_state_report.charge_power", "8.5"),
        ]))
        d = vw_euda.state_values(state)
        self.assertEqual(vw_euda.soc_value(d), 50.0)
        self.assertEqual(d["battery_state_report.charge_power"], "8.5")


def _charging(remaining, capture=CAPTURE):
    """A charging reading with a given remaining time and capture time."""
    d = {"battery_level_HV.value": "50.0",
         "battery_level_HV.state": "VALID",
         "battery_state_report.charge_power": "7.0",
         "battery_state_report.remaining_charging_time_complete": remaining,
         "charging_state_report.current_charge_state":
         "CHARGE_STATE_CHARGING_HV_BATTERY"}
    if capture is not None:
        d["car_captured_utc_timestamp"] = capture
    return d


CAPTURED_AT = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)


def _at(minutes):
    return CAPTURED_AT + timedelta(minutes=minutes)


class TestBuildReadings(unittest.TestCase):
    def test_soc_is_raw_while_charging(self):
        d = vw_euda.build_field_dict([SAMPLE])
        r = vw_euda.build_readings(d, _at(60))
        self.assertEqual(r["battery_level_vw"], 42)

    def test_range_is_raw_while_charging(self):
        d = vw_euda.build_field_dict([SAMPLE])
        r = vw_euda.build_readings(d, _at(60))
        self.assertEqual(r["electric_range_vw"], 208)

    def test_other_fields_unchanged(self):
        d = vw_euda.build_field_dict([SAMPLE])
        r = vw_euda.build_readings(d, _at(60))
        self.assertEqual(r["plug_connected_vw"], 1)
        self.assertEqual(r["charge_power_vw"], 8.5)
        self.assertEqual(r["target_soc_vw"], 80)
        self.assertEqual(r["captured_vw"], CAPTURED_AT.timestamp())

    def test_no_estimation_parameters(self):
        params = list(inspect.signature(vw_euda.build_readings).parameters)
        self.assertEqual(params, ["d", "now"])
        self.assertFalse(hasattr(vw_euda, "interpolate"))


class TestTimeLeft(unittest.TestCase):
    def test_raw_time_while_fresh(self):
        r = vw_euda.build_readings(_charging("2400s"), _at(10))
        self.assertEqual(r["charging_time_left_vw"], 40)   # no countdown

    def test_boundary(self):
        d = _charging("2400s")
        self.assertEqual(
            vw_euda.build_readings(d, _at(39))["charging_time_left_vw"], 40)
        self.assertEqual(
            vw_euda.build_readings(d, _at(40))["charging_time_left_vw"], 0)
        self.assertEqual(
            vw_euda.build_readings(d, _at(41))["charging_time_left_vw"], 0)

    def test_long_charge_stays_while_fresh(self):
        d = vw_euda.build_field_dict([SAMPLE])   # 10500s = 175 min
        r = vw_euda.build_readings(d, _at(170))
        self.assertEqual(r["charging_time_left_vw"], 175)

    def test_unknown_capture_is_zero(self):
        r = vw_euda.build_readings(_charging("2400s", capture=None), _at(10))
        self.assertEqual(r["charging_time_left_vw"], 0)

    def test_not_charging_is_zero(self):
        d = {"battery_level_HV.value": "50.0",
             "battery_level_HV.state": "VALID",
             "charging_state_report.current_charge_state":
             "CHARGE_STATE_NOT_CHARGING",
             "car_captured_utc_timestamp": CAPTURE}
        r = vw_euda.build_readings(d, _at(10))
        self.assertEqual(r["battery_level_vw"], 50)
        self.assertEqual(r["charging_time_left_vw"], 0)

    def test_partial_snapshot_omits_unknowns(self):
        d = {"battery_level_HV.value": "50.0",
             "battery_level_HV.state": "VALID"}
        r = vw_euda.build_readings(d, _at(10))
        self.assertEqual(r["battery_level_vw"], 50)
        self.assertNotIn("charging_time_left_vw", r)
        self.assertNotIn("electric_range_vw", r)
        self.assertNotIn("target_soc_vw", r)
        self.assertNotIn("plug_connected_vw", r)


class TestSnapshot20260928(unittest.TestCase):
    """The frozen reading the portal served on the night of 2026-09-28."""

    def _readings(self, now):
        with open(SNAPSHOT_FILE) as fh:
            payload = json.load(fh)
        state = vw_euda.merge_capture_aware({}, payload)
        return vw_euda.build_readings(vw_euda.state_values(state), now)

    def test_frozen_snapshot_next_morning(self):
        r = self._readings(datetime(2026, 9, 29, 6, 54, tzinfo=timezone.utc))
        self.assertEqual(r["charging_time_left_vw"], 0)
        self.assertEqual(r["battery_level_vw"], 65)
        self.assertEqual(r["electric_range_vw"], 369)
        self.assertEqual(r["plug_connected_vw"], 1)
        self.assertEqual(r["charge_power_vw"], 6.700012)
        self.assertEqual(r["target_soc_vw"], 60)

    def test_snapshot_within_its_time_left(self):
        r = self._readings(datetime(2026, 9, 28, 11, 30, tzinfo=timezone.utc))
        self.assertEqual(r["charging_time_left_vw"], 40)


if __name__ == "__main__":
    unittest.main()
