import datetime
import unittest

from energyestimator import calculate


class TestEnergyEstimator(unittest.TestCase):

    def test_no_load_no_power_off_should_off(self):
        expected = {datetime.datetime(2024, 1, 26, 23, 50): {'total_tc': 1.0163, 'total_primotop': 2.6752, 'total_tc_cummulative': 1.0163, 'total_primotop_cummulative': 2.6752},
                    datetime.datetime(2024, 1, 27, 0, 50): {'total_tc': 1.05205, 'total_primotop': 2.8181999999999996, 'total_tc_cummulative': 2.0683499999999997, 'total_primotop_cummulative': 5.493399999999999},
                    datetime.datetime(2024, 1, 27, 1, 50): {'total_tc': 1.099842105263158, 'total_primotop': 2.8754, 'total_tc_cummulative': 3.1681921052631576, 'total_primotop_cummulative': 8.3688},
                    datetime.datetime(2024, 1, 27, 2, 50): {'total_tc': 1.099842105263158, 'total_primotop': 2.8754, 'total_tc_cummulative': 4.268034210526316, 'total_primotop_cummulative': 11.2442},
                    datetime.datetime(2024, 1, 27, 3, 50): {'total_tc': 1.1111315789473686, 'total_primotop': 2.9183, 'total_tc_cummulative': 5.379165789473684, 'total_primotop_cummulative': 14.1625},
                    datetime.datetime(2024, 1, 27, 4, 50): {'total_tc': 1.1688333333333334, 'total_primotop': 2.9898000000000002, 'total_tc_cummulative': 6.547999122807018, 'total_primotop_cummulative': 17.1523},
                    datetime.datetime(2024, 1, 27, 5, 50): {'total_tc': 1.1886944444444445, 'total_primotop': 3.0613, 'total_tc_cummulative': 7.7366935672514625, 'total_primotop_cummulative': 20.2136},
                    datetime.datetime(2024, 1, 27, 6, 50): {'total_tc': 1.2745833333333334, 'total_primotop': 3.1885, 'total_tc_cummulative': 9.011276900584797, 'total_primotop_cummulative': 23.4021},
                    datetime.datetime(2024, 1, 27, 7, 50): {'total_tc': 1.3547222222222222, 'total_primotop': 3.2169999999999996, 'total_tc_cummulative': 10.365999122807018, 'total_primotop_cummulative': 26.6191},
                    datetime.datetime(2024, 1, 27, 8, 50): {'total_tc': 1.4348947368421054, 'total_primotop': 3.2525999999999997, 'total_tc_cummulative': 11.800893859649124, 'total_primotop_cummulative': 29.8717},
                    datetime.datetime(2024, 1, 27, 9, 50): {'total_tc': 1.518475, 'total_primotop': 3.2739000000000003, 'total_tc_cummulative': 13.319368859649124, 'total_primotop_cummulative': 33.1456},
                    datetime.datetime(2024, 1, 27, 10, 50): {'total_tc': 1.67915, 'total_primotop': 3.3165999999999998, 'total_tc_cummulative': 14.998518859649124, 'total_primotop_cummulative': 36.4622},
                    datetime.datetime(2024, 1, 27, 11, 50): {'total_tc': 2.65055, 'total_primotop': 6.7021999999999995, 'total_tc_cummulative': 17.649068859649123, 'total_primotop_cummulative': 43.1644},
                    datetime.datetime(2024, 1, 27, 12, 50): {'total_tc': 1.7933999999999999, 'total_primotop': 4.5736, 'total_tc_cummulative': 19.44246885964912, 'total_primotop_cummulative': 47.738},
                    datetime.datetime(2024, 1, 27, 13, 50): {'total_tc': 1.146975, 'total_primotop': 2.6879, 'total_tc_cummulative': 20.589443859649123, 'total_primotop_cummulative': 50.4259},
                    datetime.datetime(2024, 1, 27, 14, 50): {'total_tc': 1.468425, 'total_primotop': 3.0736999999999997, 'total_tc_cummulative': 22.057868859649123, 'total_primotop_cummulative': 53.4996},
                    datetime.datetime(2024, 1, 27, 15, 50): {'total_tc': 1.5077500000000001, 'total_primotop': 3.231, 'total_tc_cummulative': 23.565618859649124, 'total_primotop_cummulative': 56.7306},
                    datetime.datetime(2024, 1, 27, 16, 50): {'total_tc': 1.2660789473684213, 'total_primotop': 3.0311, 'total_tc_cummulative': 24.831697807017544, 'total_primotop_cummulative': 59.761700000000005},
                    datetime.datetime(2024, 1, 27, 17, 50): {'total_tc': 1.1848947368421054, 'total_primotop': 3.0025999999999997, 'total_tc_cummulative': 26.01659254385965,
                                                             'total_primotop_cummulative': 62.764300000000006},
                    datetime.datetime(2024, 1, 27, 18, 50): {'total_tc': 1.2586944444444446, 'total_primotop': 3.1313, 'total_tc_cummulative': 27.275286988304096, 'total_primotop_cummulative': 65.8956},
                    datetime.datetime(2024, 1, 27, 19, 50): {'total_tc': 1.2785555555555557, 'total_primotop': 3.2028, 'total_tc_cummulative': 28.553842543859652, 'total_primotop_cummulative': 69.0984},
                    datetime.datetime(2024, 1, 27, 20, 50): {'total_tc': 1.3171428571428572, 'total_primotop': 3.26, 'total_tc_cummulative': 29.87098540100251, 'total_primotop_cummulative': 72.3584},
                    datetime.datetime(2024, 1, 27, 21, 50): {'total_tc': 1.3294000000000001, 'total_primotop': 3.3028999999999997, 'total_tc_cummulative': 31.20038540100251, 'total_primotop_cummulative': 75.6613},
                    datetime.datetime(2024, 1, 27, 22, 50): {'total_tc': 1.2675714285714286, 'total_primotop': 3.2615, 'total_tc_cummulative': 32.467956829573936, 'total_primotop_cummulative': 78.9228}}

        test_data = {"1706310000.0": 1.6, "1706313600.0": 0.6, "1706317200.0": 0.2, "1706320800.0": 0.2, "1706324400.0": -0.1, "1706328000.0": -0.6, "1706331600.0": -1.1, "1706335200.0": -1.5, "1706338800.0": -1.0,
                     "1706342400.0": -0.2, "1706346000.0": 0.7, "1706349600.0": 1.8, "1706353200.0": 2.6, "1706356800.0": 2.8, "1706360400.0": 2.7, "1706364000.0": 2.1, "1706367600.0": 1.0, "1706371200.0": 0.3,
                     "1706374800.0": -0.2, "1706378400.0": -1.1, "1706382000.0": -1.6, "1706385600.0": -2.0, "1706389200.0": -2.3, "1706392800.0": -2.5}
        print(calculate(test_data))
        self.assertEqual(expected, calculate(test_data))


if __name__ == '__main__':
    unittest.main()
