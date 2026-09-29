import asyncio
import io
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock heavy external dependency that may not be installed locally
sys.modules.setdefault('goodwe', MagicMock())

import common  # noqa: E402
import inverter_setter  # noqa: E402
from inverter_setter import charging_curve, target_current  # noqa: E402


# Expected charge current per SOC, from ../kb/work/001-charging-curve-soc-gap/spec.md section 2.
# Index = SOC in %. Written as ranges here and expanded once; not a copy of the production table.
_RANGES = (
    (0, 40, 20),
    (41, 50, 18),
    (51, 60, 15),
    (61, 70, 13),
    (71, 80, 10),
    (81, 85, 8),
    (86, 90, 6),
    (91, 100, 4),
)
EXPECTED = [None] * 101
for _lo, _hi, _amps in _RANGES:
    for _soc in range(_lo, _hi + 1):
        EXPECTED[_soc] = _amps
assert None not in EXPECTED


class TestChargingCurve(unittest.TestCase):

    def test_every_soc_matches_table(self):
        for soc in range(0, 101):
            self.assertEqual(EXPECTED[soc], charging_curve(soc), soc)

    def test_never_rises_with_soc(self):
        for soc in range(0, 100):
            self.assertLessEqual(charging_curve(soc + 1), charging_curve(soc), f"{soc} -> {soc + 1}")

    def test_soc_92_is_4_amps(self):
        self.assertEqual(4, charging_curve(92))

    def test_out_of_range_soc(self):
        self.assertEqual(20, charging_curve(-1))
        self.assertEqual(4, charging_curve(101))


class TestTargetCurrent(unittest.TestCase):

    def test_stop_100_soc_92_is_4(self):
        self.assertEqual(4, target_current(92, 100))

    def test_stop_90_soc_92_is_0(self):
        self.assertEqual(0, target_current(92, 90))

    def test_soc_equal_to_stop_is_0(self):
        self.assertEqual(0, target_current(90, 90))
        self.assertEqual(6, target_current(89, 90))


class TestResubscribe(unittest.TestCase):
    """Change 020, D9: inverter_setter subscribes again after an MQTT reconnect."""

    TOPICS = ['command/InverterDepthOfDischarge', 'command/InverterStopChargingAt', 'home/FVE/soc']

    def test_subscribes_on_each_connect(self):
        client = common.new_client("test020-inverter_setter")
        client.subscribe = MagicMock()
        inverter_setter.subscribe(client, self.TOPICS)
        self.assertEqual(client.subscribe.call_count, 0)
        with patch("sys.stdout", new_callable=io.StringIO):
            client.on_connect(client, None, {}, 0, None)
            client.on_connect(client, None, {}, 0, None)
        self.assertEqual([c.args[0] for c in client.subscribe.call_args_list], self.TOPICS * 2)


class TestWriteFailure(unittest.TestCase):
    """Change 020: a failed GoodWe write writes one ERROR, then raises as before."""

    def test_charge_current_write_failure(self):
        inverter = MagicMock()
        inverter.write_setting = AsyncMock(side_effect=OSError("udp timeout"))
        with patch.object(inverter_setter.goodwe, "connect", new=AsyncMock(return_value=inverter)), \
                patch.object(inverter_setter, "last_curr_set", -1), \
                patch.object(inverter_setter, "soc", 50), \
                patch.object(inverter_setter, "stop_charging_at_soc", 90), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(OSError):
                asyncio.run(inverter_setter.handle_inverter_battery_charge_current())
        self.assertEqual(out.getvalue().count("ERROR inverter_setter:"), 1)

    def test_dod_write_failure(self):
        inverter = MagicMock()
        inverter.set_ongrid_battery_dod = AsyncMock(side_effect=OSError("udp timeout"))
        with patch.object(inverter_setter.goodwe, "connect", new=AsyncMock(return_value=inverter)), \
                patch.object(inverter_setter, "last_dod_set", -1), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(OSError):
                asyncio.run(inverter_setter.handle_inverter_depth_of_discharge(80))
        self.assertEqual(out.getvalue().count("ERROR inverter_setter:"), 1)


if __name__ == '__main__':
    unittest.main()
