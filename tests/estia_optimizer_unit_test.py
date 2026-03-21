import unittest
from unittest.mock import patch

from estia_optimizer import decide, loop
import estia_optimizer


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


    def _reset_globals(self, last_last=100.0, last=100.0, target=27.0):
        estia_optimizer.last_last_water_temp = last_last
        estia_optimizer.last_water_temp = last
        estia_optimizer.target_temp = target

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_loop_reeval_does_not_break_trend(self, mock_rehau, mock_netatmo):
        """Calling loop() with current last_water_temp (as Termostat1NP does)
        should not flatten the history and break subsequent trend detection."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        # Simulate Termostat1NP triggering loop with current last_water_temp
        loop(estia_optimizer.last_water_temp)

        # History should be preserved for the next real water temp update
        self.assertEqual(estia_optimizer.last_last_water_temp, 25.0)
        self.assertEqual(estia_optimizer.last_water_temp, 26.0)

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_loop_reeval_repeated_does_not_break_trend(self, mock_rehau,
                                                        mock_netatmo):
        """Multiple rapid re-evals (grafana_setter publishes every 5s)
        should not corrupt the water temp history."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        for _ in range(10):
            loop(estia_optimizer.last_water_temp)

        self.assertEqual(estia_optimizer.last_last_water_temp, 25.0)
        self.assertEqual(estia_optimizer.last_water_temp, 26.0)

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_loop_reeval_then_real_temp_detects_trend(self, mock_rehau,
                                                       mock_netatmo):
        """After a re-eval from Termostat1NP, a real water temp update
        should still detect the upward trend and start heating."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        # Re-eval from Termostat1NP
        loop(estia_optimizer.last_water_temp)
        mock_rehau.assert_not_called()

        # Real water temp arrives
        loop(27.0)
        mock_rehau.assert_called_once_with("start")

    @patch('estia_optimizer.netatmo_set')
    @patch('estia_optimizer.rehau_set')
    def test_loop_real_temp_still_shifts_history(self, mock_rehau,
                                                  mock_netatmo):
        """A real new water temp value should still shift the history."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        loop(27.0)

        self.assertEqual(estia_optimizer.last_last_water_temp, 26.0)
        self.assertEqual(estia_optimizer.last_water_temp, 27.0)


if __name__ == '__main__':
    unittest.main()
