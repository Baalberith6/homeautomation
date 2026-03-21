import unittest

import wallbox
from wallbox import calculate_current, clean_data

class TestWallbox3Phase(unittest.TestCase):
    def setUp(self):
        clean_data()

    def test_no_load_no_power_off_should_off(self):
        test_data = {
            "ppv": 0,
            "load_p1": 0,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertEqual(0, calculate_current(test_data, 0))

    def test_no_load_8k_power_off_86p_should_on(self):
        test_data = {
            "ppv": 8000,
            "load_p1": 0,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 86
        }
        self.assertEqual(12, calculate_current(test_data, 0))

    def test_no_load_8k_power_off_100p_should_on(self):
        test_data = {
            "ppv": 8000,
            "load_p1": 0,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertEqual(12, calculate_current(test_data, 0))

    def test_4k_load_no_power_on_89p_should_on(self):
        test_data = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 89
        }
        self.assertEqual(6, calculate_current(test_data, 6))

    def test_4k_load_no_power_on_5p_under_should_off(self):
        test_data = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 80
        }
        self.assertEqual(6, calculate_current(test_data, 6))
        test_data_2 = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 75
        }
        self.assertEqual(0, calculate_current(test_data_2, 6))

    def test_4k_load_no_power_on_2p_under_should_on(self):
        test_data = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 80
        }
        self.assertEqual(6, calculate_current(test_data, 6))
        test_data_2 = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 78
        }
        self.assertEqual(6, calculate_current(test_data_2, 6))

    def test_soc_keeps_updating(self):
        test_data = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 60
        }
        self.assertEqual(6, calculate_current(test_data, 6))
        test_data_2 = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 70
        }
        self.assertEqual(6, calculate_current(test_data_2, 6))
        test_data_3 = {
            "ppv": 0,
            "load_p1": 1380,
            "load_p2": 1380,
            "load_p3": 1380,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 65
        }
        self.assertEqual(0, calculate_current(test_data_3, 6))


    def test_manual_8k_load_no_power_on_66p_should_on(self):
        test_data = {
            "ppv": 0,
            "load_p1": 2760,
            "load_p2": 2760,
            "load_p3": 2760,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 66
        }
        self.assertEqual(6, calculate_current(test_data, 12))

    def test_8k_load_10k_power_on_85p_should_increase(self):
        test_data = {
            "ppv": 10000,
            "load_p1": 2760,
            "load_p2": 2760,
            "load_p3": 2760,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 85
        }
        self.assertEqual(15, calculate_current(test_data, 12))

    def test_8k_load_7k_power_on_85p_should_decrease(self):
        test_data = {
            "ppv": 7000,
            "load_p1": 2760,
            "load_p2": 2760,
            "load_p3": 2760,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 85
        }
        self.assertEqual(11, calculate_current(test_data, 12))

    def test_8k_load_20k_power_on_85p_should_max(self):
        test_data = {
            "ppv": 20000,
            "load_p1": 2760,
            "load_p2": 2760,
            "load_p3": 2760,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 85
        }
        self.assertEqual(16, calculate_current(test_data, 12))


class TestWallboxStartSOCGate(unittest.TestCase):
    """Not charging + plenty of PV but battery SOC below wallboxStartSOC → should not start"""
    def setUp(self):
        clean_data()

    def test_not_charging_soc_below_start_threshold_should_not_start(self):
        test_data = {
            "ppv": 10000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 30  # below wallboxStartSOC (40)
        }
        self.assertEqual(0, calculate_current(test_data, 0))

    def test_not_charging_soc_at_start_threshold_should_not_start(self):
        test_data = {
            "ppv": 10000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 40  # equal to wallboxStartSOC — condition is strict >
        }
        self.assertEqual(0, calculate_current(test_data, 0))

    def test_not_charging_soc_just_above_start_threshold_should_start(self):
        test_data = {
            "ppv": 10000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 41  # just above wallboxStartSOC
        }
        self.assertGreater(calculate_current(test_data, 0), 0)


class TestWallboxStartMode(unittest.TestCase):
    """wallboxMode == 'Start' forces wallboxMaxAmp regardless of PV"""
    def setUp(self):
        clean_data()
        self._orig_mode = wallbox.wallboxMode
        wallbox.wallboxMode = "Start"

    def tearDown(self):
        wallbox.wallboxMode = self._orig_mode

    def test_start_mode_not_charging_no_pv_should_force_max(self):
        test_data = {
            "ppv": 0,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 50
        }
        self.assertEqual(16, calculate_current(test_data, 0))

    def test_start_mode_charging_no_pv_should_keep_max(self):
        test_data = {
            "ppv": 0,
            "load_p1": 2760, "load_p2": 2760, "load_p3": 2760,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 50
        }
        self.assertEqual(16, calculate_current(test_data, 12))

    def test_start_mode_low_soc_should_still_charge(self):
        test_data = {
            "ppv": 0,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 10  # below wallboxStartSOC, but Start mode ignores it
        }
        self.assertEqual(16, calculate_current(test_data, 0))


class TestWallboxAsymmetricLoad(unittest.TestCase):
    """Unbalanced load across phases should produce different results due to max(i1,i2,i3)"""
    def setUp(self):
        clean_data()

    def test_heavy_load_on_one_phase_reduces_allowable(self):
        # All load on P1, nothing on P2/P3
        test_data = {
            "ppv": 8000,
            "load_p1": 3000, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        result_asymmetric = calculate_current(test_data, 0)
        clean_data()
        # Same total load spread evenly
        test_data_even = {
            "ppv": 8000,
            "load_p1": 1000, "load_p2": 1000, "load_p3": 1000,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        result_even = calculate_current(test_data_even, 0)
        # Asymmetric load should allow fewer amps (max phase current is higher)
        self.assertLessEqual(result_asymmetric, result_even)


class TestWallboxBackupCurrent(unittest.TestCase):
    """backup_i adds directly to phase current — meaningful values should reduce allowable"""
    def setUp(self):
        clean_data()

    def test_backup_current_reduces_allowable(self):
        # No backup current
        test_data_no_backup = {
            "ppv": 8000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        result_no_backup = calculate_current(test_data_no_backup, 0)
        clean_data()
        # 3A backup per phase (690W each = 2070W total drawn from backup)
        test_data_backup = {
            "ppv": 8000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 3, "backup_i2": 3, "backup_i3": 3,
            "battery_soc": 100
        }
        result_backup = calculate_current(test_data_backup, 0)
        self.assertLess(result_backup, result_no_backup)


class TestWallboxAmpReserve(unittest.TestCase):
    """amp_reserve holds back PV for the house"""
    def setUp(self):
        clean_data()
        self._orig_reserve = wallbox.amp_reserve

    def tearDown(self):
        wallbox.amp_reserve = self._orig_reserve

    def test_positive_reserve_reduces_allowable(self):
        test_data = {
            "ppv": 8000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = -1  # default
        result_default = calculate_current(test_data, 0)
        clean_data()
        wallbox.amp_reserve = 3
        result_reserved = calculate_current(test_data, 0)
        self.assertLess(result_reserved, result_default)

    def test_reserve_reduces_by_expected_amount(self):
        """With 10kW PV, no load, reserve=0 vs reserve=3 should differ by ~3A
        (reserve holds back 3A * 3 phases * 230V = 2070W)."""
        test_data = {
            "ppv": 10000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 0
        result_no_reserve = calculate_current(test_data, 0)
        clean_data()
        wallbox.amp_reserve = 3
        result_reserved = calculate_current(test_data, 0)
        # 3A reserve = 2070W less → should be ~3A less
        self.assertEqual(result_no_reserve - result_reserved, 3)

    def test_reserve_prevents_starting_when_not_enough_pv(self):
        """Not charging yet — reserve reduces available PV below start
        threshold, so charging should not start."""
        test_data = {
            "ppv": 5000,  # not enough for 6A charging + 3A reserve
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 3
        result = calculate_current(test_data, 0)
        self.assertEqual(0, result)

    def test_reserve_triggers_decrease_while_charging(self):
        """While charging at 8A, reserve=4 reduces available PV — current
        should decrease but not stop; caps at minimum (6A)."""
        # Charging at 8A → load includes wallbox: 8*230=1840 per phase
        test_data = {
            "ppv": 7000,
            "load_p1": 1840, "load_p2": 1840, "load_p3": 1840,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 4
        result = calculate_current(test_data, 8)
        self.assertEqual(6, result)

    def test_reserve_does_not_stop_charging(self):
        """Even with very high reserve and no PV, charging should cap at
        minimum (6A) instead of stopping."""
        # Charging at 10A → load includes wallbox: 10*230=2300 per phase
        test_data = {
            "ppv": 0,
            "load_p1": 2300, "load_p2": 2300, "load_p3": 2300,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 5
        result = calculate_current(test_data, 10)
        self.assertEqual(6, result)

    def test_negative_reserve_increases_allowable(self):
        """Negative reserve draws from battery to charge faster than PV alone."""
        test_data = {
            "ppv": 5000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 0
        result_no_reserve = calculate_current(test_data, 0)
        clean_data()
        wallbox.amp_reserve = -3
        result_negative = calculate_current(test_data, 0)
        # -3A reserve adds 3*3*230=2070W headroom → ~3A more
        self.assertEqual(result_negative - result_no_reserve, 3)

    def test_negative_reserve_starts_charging_below_pv_threshold(self):
        """With negative reserve, can start charging even when PV alone
        wouldn't be enough — draws the difference from battery."""
        test_data = {
            "ppv": 3000,  # only ~4A worth, below start_at=6
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        wallbox.amp_reserve = 0
        result_no_reserve = calculate_current(test_data, 0)
        self.assertEqual(0, result_no_reserve)  # can't start without reserve
        clean_data()
        wallbox.amp_reserve = -3  # adds 2070W → 5070W total → 7A
        result_negative = calculate_current(test_data, 0)
        self.assertGreaterEqual(result_negative, 6)


class TestWallboxStartThreshold(unittest.TestCase):
    """Not enough PV to reach start_at (6A) → should not start"""
    def setUp(self):
        clean_data()

    def test_just_below_start_threshold_should_not_start(self):
        # 5A * 3 phases * 230V = 3450W needed to reach 5A (below start_at=6)
        # With some load, even less available
        test_data = {
            "ppv": 3000,  # not enough for 6A * 3 * 230 = 4140W
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertEqual(0, calculate_current(test_data, 0))

    def test_just_at_start_threshold_should_start(self):
        # 6A * 3 * 230 = 4140W + amp_reserve headroom
        test_data = {
            "ppv": 5000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertGreaterEqual(calculate_current(test_data, 0), 6)


class TestWallboxMaxSocReset(unittest.TestCase):
    """maxSocWhileCharging resets on stop, then fresh tracking on restart"""
    def setUp(self):
        clean_data()

    def test_reset_and_restart_cycle(self):
        # Start charging at SOC 80
        data_80 = {
            "ppv": 8000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 80
        }
        result = calculate_current(data_80, 6)
        self.assertGreater(result, 0)
        # SOC drops to 74 (6 below max of 80, exceeds wallboxStopAtSOCDiff=3) → stop
        data_74 = {
            "ppv": 0,
            "load_p1": 1380, "load_p2": 1380, "load_p3": 1380,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 74
        }
        result = calculate_current(data_74, 6)
        self.assertEqual(0, result)
        # Now restart with plenty of PV at SOC 60 — should work fresh
        data_60 = {
            "ppv": 10000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 60
        }
        result = calculate_current(data_60, 0)
        self.assertGreater(result, 0)


class TestWallboxCustomMaxAmp(unittest.TestCase):
    """Custom wallboxMaxAmp caps the output"""
    def setUp(self):
        clean_data()
        self._orig_max = wallbox.wallboxMaxAmp

    def tearDown(self):
        wallbox.wallboxMaxAmp = self._orig_max

    def test_lower_max_amp_caps_output(self):
        wallbox.wallboxMaxAmp = 10
        test_data = {
            "ppv": 20000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertEqual(10, calculate_current(test_data, 0))

    def test_lower_max_amp_caps_while_charging(self):
        wallbox.wallboxMaxAmp = 8
        test_data = {
            "ppv": 20000,
            "load_p1": 0, "load_p2": 0, "load_p3": 0,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 100
        }
        self.assertEqual(8, calculate_current(test_data, 6))


class TestWallboxSOCDropBoundary(unittest.TestCase):
    """Exact boundary: SOC drop == wallboxStopAtSOCDiff (3) should keep charging, drop > 3 should stop"""
    def setUp(self):
        clean_data()

    def test_soc_drop_exactly_at_diff_keeps_charging(self):
        # Establish max SOC at 80
        data_80 = {
            "ppv": 0,
            "load_p1": 1380, "load_p2": 1380, "load_p3": 1380,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 80
        }
        calculate_current(data_80, 6)
        # Drop exactly 3 (to 77) — condition is >= maxSoc - diff, so 77 >= 80-3 = 77 → keep
        data_77 = {
            "ppv": 0,
            "load_p1": 1380, "load_p2": 1380, "load_p3": 1380,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 77
        }
        self.assertGreater(calculate_current(data_77, 6), 0)

    def test_soc_drop_beyond_diff_stops_charging(self):
        clean_data()
        # Establish max SOC at 80
        data_80 = {
            "ppv": 0,
            "load_p1": 1380, "load_p2": 1380, "load_p3": 1380,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 80
        }
        calculate_current(data_80, 6)
        # Drop 4 (to 76) — 76 >= 80-3=77 is False → stop
        data_76 = {
            "ppv": 0,
            "load_p1": 1380, "load_p2": 1380, "load_p3": 1380,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "battery_soc": 76
        }
        self.assertEqual(0, calculate_current(data_76, 6))


if __name__ == '__main__':
    unittest.main()
