import datetime
import unittest

from energyestimator import calculate


class TestEnergyEstimator(unittest.TestCase):

    def test(self):
        expected = {datetime.datetime(2024, 1, 26, 23, 50): {'total_tc': 1.0863, 'total_primotop': 2.7451999999999996, 'total_tc_cummulative': 1.0863, 'total_primotop_cummulative': 2.7451999999999996},
                    datetime.datetime(2024, 1, 27, 0, 50): {'total_tc': 1.12205, 'total_primotop': 2.8881999999999994, 'total_tc_cummulative': 2.2083500000000003, 'total_primotop_cummulative': 5.633399999999999},
                    datetime.datetime(2024, 1, 27, 1, 50): {'total_tc': 1.169842105263158, 'total_primotop': 2.9454, 'total_tc_cummulative': 3.3781921052631585, 'total_primotop_cummulative': 8.5788},
                    datetime.datetime(2024, 1, 27, 2, 50): {'total_tc': 1.169842105263158, 'total_primotop': 2.9454, 'total_tc_cummulative': 4.548034210526317, 'total_primotop_cummulative': 11.524199999999999},
                    datetime.datetime(2024, 1, 27, 3, 50): {'total_tc': 1.1811315789473684, 'total_primotop': 2.9882999999999997, 'total_tc_cummulative': 5.729165789473685, 'total_primotop_cummulative': 14.5125},
                    datetime.datetime(2024, 1, 27, 4, 50): {'total_tc': 1.2388333333333335, 'total_primotop': 3.0598, 'total_tc_cummulative': 6.967999122807019, 'total_primotop_cummulative': 17.5723},
                    datetime.datetime(2024, 1, 27, 5, 50): {'total_tc': 1.2586944444444446, 'total_primotop': 3.1313, 'total_tc_cummulative': 8.226693567251463, 'total_primotop_cummulative': 20.703599999999998},
                    datetime.datetime(2024, 1, 27, 6, 50): {'total_tc': 1.3445833333333335, 'total_primotop': 3.2584999999999997, 'total_tc_cummulative': 9.571276900584795, 'total_primotop_cummulative': 23.9621},
                    datetime.datetime(2024, 1, 27, 7, 50): {'total_tc': 1.424722222222222, 'total_primotop': 3.2869999999999995, 'total_tc_cummulative': 10.995999122807017, 'total_primotop_cummulative': 27.2491},
                    datetime.datetime(2024, 1, 27, 8, 50): {'total_tc': 1.4848947368421053, 'total_primotop': 3.3026, 'total_tc_cummulative': 12.480893859649122, 'total_primotop_cummulative': 30.551699999999997},
                    datetime.datetime(2024, 1, 27, 9, 50): {'total_tc': 1.518475, 'total_primotop': 3.2739000000000003, 'total_tc_cummulative': 13.999368859649122, 'total_primotop_cummulative': 33.825599999999994},
                    datetime.datetime(2024, 1, 27, 10, 50): {'total_tc': 1.67915, 'total_primotop': 3.3165999999999998, 'total_tc_cummulative': 15.678518859649122, 'total_primotop_cummulative': 37.142199999999995},
                    datetime.datetime(2024, 1, 27, 11, 50): {'total_tc': 2.7205500000000002, 'total_primotop': 6.7722, 'total_tc_cummulative': 18.399068859649123, 'total_primotop_cummulative': 43.91439999999999},
                    datetime.datetime(2024, 1, 27, 12, 50): {'total_tc': 1.8634, 'total_primotop': 4.643599999999999, 'total_tc_cummulative': 20.262468859649122, 'total_primotop_cummulative': 48.55799999999999},
                    datetime.datetime(2024, 1, 27, 13, 50): {'total_tc': 1.146975, 'total_primotop': 2.6879, 'total_tc_cummulative': 21.409443859649123, 'total_primotop_cummulative': 51.24589999999999},
                    datetime.datetime(2024, 1, 27, 14, 50): {'total_tc': 1.468425, 'total_primotop': 3.0736999999999997, 'total_tc_cummulative': 22.877868859649123, 'total_primotop_cummulative': 54.319599999999994},
                    datetime.datetime(2024, 1, 27, 15, 50): {'total_tc': 1.5077500000000001, 'total_primotop': 3.231, 'total_tc_cummulative': 24.385618859649124, 'total_primotop_cummulative': 57.550599999999996},
                    datetime.datetime(2024, 1, 27, 16, 50): {'total_tc': 1.2660789473684213, 'total_primotop': 3.0311, 'total_tc_cummulative': 25.651697807017545, 'total_primotop_cummulative': 60.5817},
                    datetime.datetime(2024, 1, 27, 17, 50): {'total_tc': 1.2848947368421053, 'total_primotop': 3.1026,
                                                             'total_tc_cummulative': 26.93659254385965, 'total_primotop_cummulative': 63.6843},
                    datetime.datetime(2024, 1, 27, 18, 50): {'total_tc': 1.3586944444444446, 'total_primotop': 3.2313, 'total_tc_cummulative': 28.295286988304095, 'total_primotop_cummulative': 66.9156},
                    datetime.datetime(2024, 1, 27, 19, 50): {'total_tc': 1.3785555555555558, 'total_primotop': 3.3028, 'total_tc_cummulative': 29.67384254385965, 'total_primotop_cummulative': 70.2184},
                    datetime.datetime(2024, 1, 27, 20, 50): {'total_tc': 1.4171428571428573, 'total_primotop': 3.36, 'total_tc_cummulative': 31.090985401002506, 'total_primotop_cummulative': 73.5784},
                    datetime.datetime(2024, 1, 27, 21, 50): {'total_tc': 1.4294, 'total_primotop': 3.4029, 'total_tc_cummulative': 32.52038540100251, 'total_primotop_cummulative': 76.9813},
                    datetime.datetime(2024, 1, 27, 22, 50): {'total_tc': 1.3375714285714286, 'total_primotop': 3.3314999999999997, 'total_tc_cummulative': 33.857956829573936, 'total_primotop_cummulative': 80.31280000000001}}

        test_data = {"1706310000.0": 1.6, "1706313600.0": 0.6, "1706317200.0": 0.2, "1706320800.0": 0.2, "1706324400.0": -0.1, "1706328000.0": -0.6, "1706331600.0": -1.1, "1706335200.0": -1.5, "1706338800.0": -1.0,
                     "1706342400.0": -0.2, "1706346000.0": 0.7, "1706349600.0": 1.8, "1706353200.0": 2.6, "1706356800.0": 2.8, "1706360400.0": 2.7, "1706364000.0": 2.1, "1706367600.0": 1.0, "1706371200.0": 0.3,
                     "1706374800.0": -0.2, "1706378400.0": -1.1, "1706382000.0": -1.6, "1706385600.0": -2.0, "1706389200.0": -2.3, "1706392800.0": -2.5}
        self.assertEqual(expected, calculate(test_data))


if __name__ == '__main__':
    unittest.main()
