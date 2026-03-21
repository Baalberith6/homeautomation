import unittest
from unittest.mock import patch

from estia_optimizer import decide


class TestEstiaOptimizer(unittest.TestCase):

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_up_below_target_starts_heating(self, mock_rehau,
                                                   mock_netatmo):
        # Temps rising: 25 → 26 → 27, target=30, hysteresis=3
        # 27 < 30 + 3 = 33, so should start
        decide(25.0, 26.0, 27.0, 30.0)
        mock_rehau.assert_called_once_with("start")
        mock_netatmo.assert_called_once()

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_up_well_below_target_uses_long_time(self, mock_rehau,
                                                        mock_netatmo):
        # new_water_temp (27) < target + 0.5 (30.5) → 1800s
        decide(25.0, 26.0, 27.0, 30.0)
        mock_netatmo.assert_called_once_with(op="start", add_time=1800)

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_up_near_target_uses_short_time(self, mock_rehau,
                                                   mock_netatmo):
        # new_water_temp (30.8) >= target + 0.5 (30.5) → 900s
        # But still < target + hysteresis (33) so heating starts
        decide(29.0, 30.0, 30.8, 30.0)
        mock_netatmo.assert_called_once_with(op="start", add_time=900)

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_up_above_hysteresis_does_nothing(self, mock_rehau,
                                                     mock_netatmo):
        # new_water_temp (34) >= target + hysteresis (30 + 3 = 33)
        decide(32.0, 33.0, 34.0, 30.0)
        mock_rehau.assert_not_called()
        mock_netatmo.assert_not_called()

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_down_stops_heating(self, mock_rehau, mock_netatmo):
        # Temps falling: 30 → 29 → 28
        decide(30.0, 29.0, 28.0, 30.0)
        mock_rehau.assert_called_once_with("stop")
        mock_netatmo.assert_not_called()

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_no_trend_does_nothing(self, mock_rehau, mock_netatmo):
        # Temps: 28 → 29 → 28.5 (not monotonically rising or falling)
        decide(28.0, 29.0, 28.5, 30.0)
        mock_rehau.assert_not_called()
        mock_netatmo.assert_not_called()

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_flat_temps_does_nothing(self, mock_rehau, mock_netatmo):
        # All same
        decide(28.0, 28.0, 28.0, 30.0)
        mock_rehau.assert_not_called()
        mock_netatmo.assert_not_called()

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_trend_up_at_exact_hysteresis_boundary(self, mock_rehau,
                                                    mock_netatmo):
        # new_water_temp (33) == target + hysteresis (30 + 3)
        # Condition is < not <=, so should NOT start
        decide(31.0, 32.0, 33.0, 30.0)
        mock_rehau.assert_not_called()
        mock_netatmo.assert_not_called()


if __name__ == '__main__':
    unittest.main()
