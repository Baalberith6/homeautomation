import unittest

from wallbox import calculate_current, clean_data
from config import wallboxConfig

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
        self.assertEqual(0, calculate_current(test_data, 0, 3))

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
        self.assertEqual(12, calculate_current(test_data, 0, 3))

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
        self.assertEqual(12, calculate_current(test_data, 0, 3))

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
        self.assertEqual(6, calculate_current(test_data, 6, 3))

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
        self.assertEqual(6, calculate_current(test_data, 6, 3))
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
        self.assertEqual(0, calculate_current(test_data_2, 6, 3))

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
        self.assertEqual(6, calculate_current(test_data, 6, 3))
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
        self.assertEqual(6, calculate_current(test_data_2, 6, 3))

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
        self.assertEqual(6, calculate_current(test_data, 6, 3))
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
        self.assertEqual(6, calculate_current(test_data_2, 6, 3))
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
        self.assertEqual(0, calculate_current(test_data_3, 6, 3))


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
        self.assertEqual(6, calculate_current(test_data, 12, 3))

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
        self.assertEqual(15, calculate_current(test_data, 12, 3))

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
        self.assertEqual(11, calculate_current(test_data, 12, 3))

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
        self.assertEqual(15, calculate_current(test_data, 12, 3))


class TestWallbox1Phase(unittest.TestCase):
    def setUp(self):
        clean_data()
    def test_no_load_4k_power_off_95p_should_on(self):
        test_data = {
            "ppv": 4000,
            "load_p1": 0,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 95
        }
        self.assertEqual(14, calculate_current(test_data, 0, 1))

    def test_no_load_4k_power_on_95p_should_increase(self):
        test_data = {
            "ppv": 4000,
            "load_p1": 1380,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 95
        }
        self.assertEqual(14, calculate_current(test_data, 6, 1))

    def test_no_load_just_started_7k_power_on_95p_should_max(self):  # just started
        test_data = {
            "ppv": 7000,
            "load_p1": 0,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 95
        }
        self.assertEqual(16, calculate_current(test_data, 6, 1))

    def test_1k_load_2k_power_off_95p_should_off(self):
        test_data = {
            "ppv": 2000,
            "load_p1": 1000,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0,
            "backup_i2": 0,
            "backup_i3": 0,
            "battery_soc": 95
        }
        self.assertEqual(0, calculate_current(test_data, 0, 1))

    def test_2k_load_10k_power_on_100p_should_on(self):
        test_data = {
            "ppv": 10000,
            "load_p1": 2000,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 100
        }
        self.assertEqual(16, calculate_current(test_data, 10, 1))

    def test_3kk_load_no_power_on_5p_under_should_off(self):
        test_data = {
            "ppv": 0,
            "load_p1": 2760,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 80
        }
        self.assertEqual(6, calculate_current(test_data, 12, 1))
        test_data = {
            "ppv": 0,
            "load_p1": 2760,
            "load_p2": 0,
            "load_p3": 0,
            "backup_i1": 0.1,
            "backup_i2": 0.1,
            "backup_i3": 0.1,
            "battery_soc": 75
        }
        self.assertEqual(0, calculate_current(test_data, 12, 1))


if __name__ == '__main__':
    unittest.main()
