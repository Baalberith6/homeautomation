import sys
import unittest
from unittest.mock import MagicMock

# Mock heavy external dependency that may not be installed locally
sys.modules.setdefault('goodwe', MagicMock())

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


if __name__ == '__main__':
    unittest.main()
