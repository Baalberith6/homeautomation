import datetime
import unittest

from energyestimator import calculate


class TestEnergyEstimator(unittest.TestCase):

    def test_no_load_no_power_off_should_off(self):
        expected = {datetime.datetime(2024, 1, 26, 23, 50): {'total_tc': 0.9448, 'total_primotop': 2.3891999999999998, 'total_tc_cummulative': 0.9448, 'total_primotop_cummulative': 2.3891999999999998},
                    datetime.datetime(2024, 1, 27, 0, 50): {'total_tc': 0.9805499999999999, 'total_primotop': 2.5322, 'total_tc_cummulative': 1.92535, 'total_primotop_cummulative': 4.9214},
                    datetime.datetime(2024, 1, 27, 1, 50): {'total_tc': 1.0245789473684213, 'total_primotop': 2.5894, 'total_tc_cummulative': 2.949928947368421, 'total_primotop_cummulative': 7.5108},
                    datetime.datetime(2024, 1, 27, 2, 50): {'total_tc': 1.0245789473684213, 'total_primotop': 2.5894, 'total_tc_cummulative': 3.974507894736842, 'total_primotop_cummulative': 10.1002},
                    datetime.datetime(2024, 1, 27, 3, 50): {'total_tc': 1.0358684210526319, 'total_primotop': 2.6323000000000003, 'total_tc_cummulative': 5.010376315789474, 'total_primotop_cummulative': 12.7325},
                    datetime.datetime(2024, 1, 27, 4, 50): {'total_tc': 1.089388888888889, 'total_primotop': 2.7038, 'total_tc_cummulative': 6.099765204678363, 'total_primotop_cummulative': 15.4363},
                    datetime.datetime(2024, 1, 27, 5, 50): {'total_tc': 1.10925, 'total_primotop': 2.7753, 'total_tc_cummulative': 7.209015204678363, 'total_primotop_cummulative': 18.2116},
                    datetime.datetime(2024, 1, 27, 6, 50): {'total_tc': 1.195138888888889, 'total_primotop': 2.9025, 'total_tc_cummulative': 8.404154093567252, 'total_primotop_cummulative': 21.1141},
                    datetime.datetime(2024, 1, 27, 7, 50): {'total_tc': 1.315, 'total_primotop': 3.074, 'total_tc_cummulative': 9.719154093567251, 'total_primotop_cummulative': 24.1881},
                    datetime.datetime(2024, 1, 27, 8, 50): {'total_tc': 1.397263157894737, 'total_primotop': 3.1095999999999995, 'total_tc_cummulative': 11.11641725146199, 'total_primotop_cummulative': 27.2977},
                    datetime.datetime(2024, 1, 27, 9, 50): {'total_tc': 1.482725, 'total_primotop': 3.1308999999999996, 'total_tc_cummulative': 12.59914225146199, 'total_primotop_cummulative': 30.4286},
                    datetime.datetime(2024, 1, 27, 10, 50): {'total_tc': 1.6434, 'total_primotop': 3.1735999999999995, 'total_tc_cummulative': 14.24254225146199, 'total_primotop_cummulative': 33.602199999999996},
                    datetime.datetime(2024, 1, 27, 11, 50): {'total_tc': 2.1148, 'total_primotop': 6.5592, 'total_tc_cummulative': 16.35734225146199, 'total_primotop_cummulative': 40.16139999999999},
                    datetime.datetime(2024, 1, 27, 12, 50): {'total_tc': 1.50765, 'total_primotop': 4.4306, 'total_tc_cummulative': 17.86499225146199, 'total_primotop_cummulative': 44.59199999999999},
                    datetime.datetime(2024, 1, 27, 13, 50): {'total_tc': 1.1112250000000001, 'total_primotop': 2.5448999999999997, 'total_tc_cummulative': 18.976217251461993,
                                                             'total_primotop_cummulative': 47.13689999999999},
                    datetime.datetime(2024, 1, 27, 14, 50): {'total_tc': 1.4326750000000001, 'total_primotop': 2.9307, 'total_tc_cummulative': 20.408892251461992, 'total_primotop_cummulative': 50.06759999999999},
                    datetime.datetime(2024, 1, 27, 15, 50): {'total_tc': 1.472, 'total_primotop': 3.088, 'total_tc_cummulative': 21.880892251461994, 'total_primotop_cummulative': 53.15559999999999},
                    datetime.datetime(2024, 1, 27, 16, 50): {'total_tc': 1.2284473684210526, 'total_primotop': 2.8880999999999997, 'total_tc_cummulative': 23.109339619883045,
                                                             'total_primotop_cummulative': 56.043699999999994},
                    datetime.datetime(2024, 1, 27, 17, 50): {'total_tc': 1.147263157894737, 'total_primotop': 2.8595999999999995, 'total_tc_cummulative': 24.256602777777783,
                                                             'total_primotop_cummulative': 58.903299999999994},
                    datetime.datetime(2024, 1, 27, 18, 50): {'total_tc': 1.2189722222222223, 'total_primotop': 2.9882999999999997, 'total_tc_cummulative': 25.475575000000006, 'total_primotop_cummulative': 61.8916},
                    datetime.datetime(2024, 1, 27, 19, 50): {'total_tc': 1.1991111111111112, 'total_primotop': 2.9168, 'total_tc_cummulative': 26.674686111111118, 'total_primotop_cummulative': 64.80839999999999},
                    datetime.datetime(2024, 1, 27, 20, 50): {'total_tc': 1.2354285714285715, 'total_primotop': 2.9739999999999998, 'total_tc_cummulative': 27.91011468253969, 'total_primotop_cummulative': 67.7824},
                    datetime.datetime(2024, 1, 27, 21, 50): {'total_tc': 1.2476857142857143, 'total_primotop': 3.0168999999999997, 'total_tc_cummulative': 29.157800396825404,
                                                             'total_primotop_cummulative': 70.79929999999999},
                    datetime.datetime(2024, 1, 27, 22, 50): {'total_tc': 1.185857142857143, 'total_primotop': 2.9755, 'total_tc_cummulative': 30.343657539682546, 'total_primotop_cummulative': 73.77479999999998}}
        test_data = {"1706310000.0": 1.6, "1706313600.0": 0.6, "1706317200.0": 0.2, "1706320800.0": 0.2, "1706324400.0": -0.1, "1706328000.0": -0.6, "1706331600.0": -1.1, "1706335200.0": -1.5, "1706338800.0": -1.0,
                     "1706342400.0": -0.2, "1706346000.0": 0.7, "1706349600.0": 1.8, "1706353200.0": 2.6, "1706356800.0": 2.8, "1706360400.0": 2.7, "1706364000.0": 2.1, "1706367600.0": 1.0, "1706371200.0": 0.3,
                     "1706374800.0": -0.2, "1706378400.0": -1.1, "1706382000.0": -1.6, "1706385600.0": -2.0, "1706389200.0": -2.3, "1706392800.0": -2.5}
        self.assertEqual(expected, calculate(test_data))


if __name__ == '__main__':
    unittest.main()
