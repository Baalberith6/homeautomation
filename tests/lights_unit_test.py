"""Change 023: the light zones follow a daily schedule through a local connection.

Spec: ../kb/work/023-light-zones-local-schedule/spec.md, sections 2, 4 and 8.
No box, no network, no real clock: a FakeDevice stands in for tinytuya.Device,
the tests patch lights.time.sleep, and due() takes `now` as a parameter.
"""
import copy
import datetime as dt
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

# The committed secret.py is a stub without the local key. Add it before lights is imported.
import secret
if not hasattr(secret, "wlBox2LocalKey"):
    secret.wlBox2LocalKey = ""
try:
    import tinytuya  # noqa: F401
except ImportError:
    sys.modules['tinytuya'] = MagicMock()

import config  # noqa: E402
import lights  # noqa: E402

ALLOWED_DPS = {"20", "21", "24", "106", "107"}


class LoopBreak(Exception):
    """Raised by a mocked sleep to leave a while True loop."""


class FakeDevice:
    """Stands in for tinytuya.Device. It keeps the selected zone and the power, as the box does."""

    def __init__(self, fail=None, report_zone=None, dp24="00ee03e8000a"):
        self.fail = fail
        self.report_zone = report_zone
        self.dp24 = dp24
        self.zone = 16
        self.power = False
        self.calls = []
        self.closed = 0

    def set_multiple_values(self, dps):
        if self.fail:
            raise self.fail
        self.calls.append(dict(dps))
        if "106" in dps:
            self.zone = dps["106"]
        if "20" in dps:
            self.power = dps["20"]
        return {"dps": dict(dps)}

    def status(self):
        zone = self.zone if self.report_zone is None else self.report_zone
        return {"dps": {"20": self.power, "21": "colour", "24": self.dp24, "106": zone, "107": zone}}

    def close(self):
        self.closed += 1


class Factory:
    """make_device() for the tests: returns the given devices in order, then the last one again."""

    def __init__(self, *devices):
        self.devices = list(devices)
        self.made = []

    def __call__(self):
        device = self.devices.pop(0) if len(self.devices) > 1 else self.devices[0]
        self.made.append(device)
        return device


def _cfg(**changes):
    cfg = copy.deepcopy(config.lightsConfig)
    cfg.update(changes)
    return cfg


def _at(h, m, s=0, day=20):
    return dt.datetime(2026, 10, day, h, m, s)


class TestConfig(unittest.TestCase):

    def test_first_table_matches_spec(self):
        cfg = config.lightsConfig
        self.assertEqual([tuple(e) for e in cfg["schedule"]], [
            ("06:00", [10, 11], "blue"),
            ("08:00", [10, 11, 12], "off"),
            ("18:00", [5, 12], "on"),
            ("18:45", [10, 11], "orange"),
            ("21:00", [10, 11], "orange_dim"),
            ("23:59", [2, 3, 5], "off"),
        ])
        self.assertEqual(cfg["colour_zones"], [10, 11])
        self.assertEqual(cfg["device_id"], "bfcb1fe44950f0d011tdkd")
        self.assertEqual(cfg["version"], 3.5)

    def test_shipped_config_is_valid(self):
        lights.check_config(config.lightsConfig)

    def test_bad_entries_raise(self):
        for entry in (("25:00", [5], "on"), ("6:00", [5], "on"), ("06:00", [0], "on"), ("06:00", [17], "on"),
                      ("06:00", [5], "green"), ("06:00", [2], "blue"), ("06:00", [], "on")):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    lights.check_config(_cfg(schedule=[entry]))


class TestColour(unittest.TestCase):

    def test_colour_hex(self):
        self.assertEqual(lights.colour_hex(30, 1000, 500), "001e03e801f4")
        self.assertEqual(lights.colour_hex(240, 1000, 500), "00f003e801f4")
        self.assertEqual(lights.colour_hex(239, 1000, 10), "00ef03e8000a")

    def test_action_dps(self):
        cfg = config.lightsConfig
        self.assertEqual(lights.action_dps("off", cfg), {"20": False})
        self.assertEqual(lights.action_dps("on", cfg), {"20": True})
        self.assertEqual(lights.action_dps("orange", cfg), {"20": True, "21": "colour", "24": "001e03e803e8"})
        self.assertEqual(lights.action_dps("blue", cfg), {"20": True, "21": "colour", "24": "00f003e803e8"})
        self.assertEqual(lights.action_dps("orange_dim", cfg), {"20": True, "21": "colour", "24": "001e03e8000a"})


class TestDue(unittest.TestCase):
    SCHEDULE = config.lightsConfig["schedule"]

    def _due(self, now, done=()):
        return lights.due(self.SCHEDULE, now, set(done), 10)

    def test_due_at_its_time(self):
        self.assertEqual(self._due(_at(18, 0, 10)), [(2, _at(18, 0))])
        self.assertEqual(self._due(_at(17, 59, 50)), [])

    def test_not_twice_in_window(self):
        done = {(2, _at(18, 0))}
        self.assertEqual(self._due(_at(18, 0, 40), done), [])
        self.assertEqual(self._due(_at(18, 9), done), [])

    def test_window_ends_after_10_min(self):
        self.assertEqual(self._due(_at(18, 9, 59)), [(2, _at(18, 0))])
        self.assertEqual(self._due(_at(18, 10, 1)), [])

    def test_2359_after_restart_at_0005(self):
        self.assertEqual(self._due(_at(0, 5, day=21)), [(5, _at(23, 59, day=20))])

    def test_2359_not_after_restart_at_0015(self):
        self.assertEqual(self._due(_at(0, 15, day=21)), [])

    def test_dim_at_2100(self):
        self.assertEqual(self._due(_at(21, 0, 10)), [(4, _at(21, 0))])

    def test_two_entries_in_time_order(self):
        self.assertEqual(self._due(_at(18, 46)), [(3, _at(18, 45))])
        schedule = [("18:05", [5], "off"), ("18:00", [12], "on")]
        self.assertEqual(lights.due(schedule, _at(18, 6), set(), 10), [(1, _at(18, 0)), (0, _at(18, 5))])


class TestTry(unittest.TestCase):

    @patch("lights.time.sleep")
    def test_try_writes_select_then_action(self, _sleep):
        device = FakeDevice()
        dps = lights.action_dps("orange", config.lightsConfig)
        self.assertIsNone(lights.try_zone(device, 10, dps, config.lightsConfig))
        self.assertEqual(device.calls, [{"106": 10, "107": 10}, dps])
        for call in device.calls:
            self.assertLessEqual(set(call), ALLOWED_DPS)

    @patch("lights.time.sleep")
    def test_wrong_zone_is_bad(self, _sleep):
        device = FakeDevice(report_zone=16)
        reason = lights.try_zone(device, 2, {"20": False}, config.lightsConfig)
        self.assertIsNotNone(reason)

    @patch("lights.time.sleep")
    def test_old_dp24_is_good(self, _sleep):
        device = FakeDevice(dp24="00ee03e8000a")
        dps = lights.action_dps("blue", config.lightsConfig)
        self.assertIsNone(lights.try_zone(device, 11, dps, config.lightsConfig))

    @patch("lights.time.sleep")
    def test_error_reply_is_bad(self, _sleep):
        device = FakeDevice()
        device.status = lambda: {"Error": "Network Error: Device Unreachable", "Err": "905"}
        reason = lights.try_zone(device, 2, {"20": False}, config.lightsConfig)
        self.assertIn("Device Unreachable", reason)


class TestRun(unittest.TestCase):

    def _run(self, fn):
        with patch("lights.time.sleep") as sleep, patch("sys.stdout", new_callable=io.StringIO) as out:
            result = fn()
        return result, out.getvalue(), [c.args[0] for c in sleep.call_args_list]

    def test_ok_at_third_try(self):
        bad = [FakeDevice(fail=OSError("timeout")), FakeDevice(fail=OSError("timeout"))]
        good = FakeDevice()
        make = Factory(*bad, good)
        ok, out, waits = self._run(lambda: lights.run_zone(make, 10, "orange", config.lightsConfig))
        self.assertTrue(ok)
        self.assertEqual(len(make.made), 3)
        self.assertEqual(len({id(d) for d in make.made}), 3)
        self.assertEqual([d.closed for d in make.made], [1, 1, 1])
        self.assertEqual(waits.count(10), 2)
        self.assertIn("INFO lights: zone 10 orange ok (try 3)", out)
        self.assertNotIn("ERROR", out)

    def test_three_bad_tries_one_error(self):
        make = Factory(FakeDevice(fail=OSError("Device Unreachable")))
        ok, out, _ = self._run(lambda: lights.run_zone(make, 2, "off", config.lightsConfig))
        self.assertFalse(ok)
        self.assertEqual(len(make.made), 3)
        self.assertEqual(out.count("ERROR lights:"), 1)
        self.assertIn("ERROR lights: zone 2 off failed: Device Unreachable", out)

    def test_failed_zone_does_not_stop_entry(self):
        broken = FakeDevice(fail=OSError("Device Unreachable"))
        devices = [broken, broken, broken, FakeDevice(), FakeDevice()]
        make = Factory(*devices)
        _, out, _ = self._run(lambda: lights.run_entry(make, [2, 3, 5], "off", config.lightsConfig))
        self.assertIn("ERROR lights: zone 2 off failed", out)
        self.assertIn("INFO lights: zone 3 off ok (try 1)", out)
        self.assertIn("INFO lights: zone 5 off ok (try 1)", out)

    def test_waits(self):
        make = Factory(FakeDevice(), FakeDevice())
        _, _, waits = self._run(lambda: lights.run_entry(make, [10, 11], "off", config.lightsConfig))
        self.assertEqual(waits, [1, 1, 2, 1, 1])


def _break_on_loop(seconds):
    """The waits inside an entry pass; the 30 s wait of the loop leaves main()."""
    if seconds == config.lightsConfig["loop_s"]:
        raise LoopBreak


class TestMain(unittest.TestCase):

    def test_bad_config_exits_1(self):
        cfg = _cfg(schedule=[("06:00", [2], "blue")])
        make = MagicMock()
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(SystemExit) as exit_:
                lights.main(cfg, make)
        self.assertEqual(exit_.exception.code, 1)
        self.assertEqual(out.getvalue().count("ERROR lights:"), 1)
        make.assert_not_called()

    @patch("lights.time.sleep", side_effect=LoopBreak)
    def test_disabled_runs_nothing(self, _sleep):
        make = MagicMock()
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                lights.main(_cfg(enabled=False), make)
        self.assertIn("INFO lights: schedule disabled", out.getvalue())
        make.assert_not_called()

    @patch("lights.time.sleep", side_effect=lambda s: _break_on_loop(s))
    def test_start_line_and_due_entry(self, _sleep):
        make = Factory(FakeDevice())
        with patch("lights.now", return_value=_at(18, 1)), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                lights.main(config.lightsConfig, make)
        self.assertIn("INFO lights: started, 6 entries, next 18:45", out.getvalue())
        self.assertIn("INFO lights: zone 5 on ok (try 1)", out.getvalue())


if __name__ == '__main__':
    unittest.main()
