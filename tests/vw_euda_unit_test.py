import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vw_euda  # noqa: E402


def _payload(fields):
    """Build an export payload from a {dataFieldName: value} dict."""
    return {"Data": [{"key": name, "dataFieldName": name, "value": val}
                     for name, val in fields.items()]}


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
})


def _interp(d, now, target=80):
    return vw_euda.interpolate(d, now, capacity_kwh=75, efficiency=0.9,
                               km_per_soc=5)


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


class TestInterpolate(unittest.TestCase):
    def test_at_capture_time_equals_reading(self):
        d = vw_euda.build_field_dict([SAMPLE])
        now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 42)
        self.assertEqual(r["electric_range_vw"], 210)
        self.assertEqual(r["charging_time_left_vw"], 175)
        self.assertEqual(r["plug_connected_vw"], 1)
        self.assertEqual(r["charge_power_vw"], 8.5)
        self.assertEqual(r["target_soc_vw"], 80)

    def test_projects_forward_while_charging(self):
        # +1h at 8.5kW into 75kWh * 0.9 = +10.2%  -> 52.2%
        d = vw_euda.build_field_dict([SAMPLE])
        now = datetime(2026, 7, 7, 13, 0, tzinfo=timezone.utc)
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 52)
        self.assertEqual(r["electric_range_vw"], 261)
        self.assertEqual(r["charging_time_left_vw"], 115)

    def test_never_overshoots_target(self):
        d = vw_euda.build_field_dict([SAMPLE])  # target 80
        now = datetime(2026, 7, 7, 20, 0, tzinfo=timezone.utc)  # +8h
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 80)

    def test_settings_target_caps_lower(self):
        d = vw_euda.build_field_dict([SAMPLE])
        d["settings.target_soc"] = "60"
        now = datetime(2026, 7, 7, 20, 0, tzinfo=timezone.utc)
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 60)
        self.assertEqual(r["target_soc_vw"], 60)

    def test_no_projection_when_idle(self):
        d = {"battery_level_HV.value": "50.0",
             "battery_level_HV.state": "VALID",
             "charging_state_report.current_charge_state":
             "CHARGE_STATE_NOT_CHARGING",
             "car_captured_utc_timestamp": CAPTURE}
        now = datetime(2026, 7, 7, 15, 0, tzinfo=timezone.utc)
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 50)
        self.assertEqual(r["charging_time_left_vw"], 0)

    def test_partial_snapshot_omits_unknowns(self):
        d = {"battery_level_HV.value": "50.0",
             "battery_level_HV.state": "VALID"}
        now = datetime(2026, 7, 7, 15, 0, tzinfo=timezone.utc)
        r = _interp(d, now)
        self.assertEqual(r["battery_level_vw"], 50)   # no capture -> no proj.
        self.assertEqual(r["electric_range_vw"], 250)
        self.assertNotIn("target_soc_vw", r)
        self.assertNotIn("plug_connected_vw", r)


if __name__ == "__main__":
    unittest.main()
