import unittest
from unittest.mock import patch

from estia_optimizer import decide, loop
import estia_optimizer


class TestEstiaOptimizer(unittest.TestCase):

    def _reset_globals(self, last_last=100.0, last=100.0, target=27.0,
                       boosting=False):
        estia_optimizer.last_last_water_temp = last_last
        estia_optimizer.last_water_temp = last
        estia_optimizer.target_temp = target
        estia_optimizer.is_boosting = boosting
        estia_optimizer.termostat_temp_1np = 21.0

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_up_below_target_starts_boosting(self, mock_apply):
        estia_optimizer.is_boosting = False
        decide(25.0, 26.0, 27.0, 30.0)
        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_up_above_hysteresis_does_nothing(self, mock_apply):
        estia_optimizer.is_boosting = False
        decide(32.0, 33.0, 34.0, 30.0)
        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_up_at_exact_hysteresis_boundary(self, mock_apply):
        # new_water_temp (33) == target + hysteresis (30 + 3)
        # Condition is < not <=, so should NOT start
        estia_optimizer.is_boosting = False
        decide(31.0, 32.0, 33.0, 30.0)
        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_down_stops_boosting(self, mock_apply):
        estia_optimizer.is_boosting = True
        decide(30.0, 29.0, 28.0, 30.0)
        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_down_when_not_boosting_does_nothing(self, mock_apply):
        estia_optimizer.is_boosting = False
        decide(30.0, 29.0, 28.0, 30.0)
        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_trend_up_when_already_boosting_does_nothing(self, mock_apply):
        estia_optimizer.is_boosting = True
        decide(25.0, 26.0, 27.0, 30.0)
        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_no_trend_does_nothing(self, mock_apply):
        estia_optimizer.is_boosting = False
        decide(28.0, 29.0, 28.5, 30.0)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_flat_temps_does_nothing(self, mock_apply):
        estia_optimizer.is_boosting = False
        decide(28.0, 28.0, 28.0, 30.0)
        mock_apply.assert_not_called()

    # --- loop / history tests ---

    @patch('estia_optimizer.apply_thermostats')
    def test_loop_reeval_does_not_break_trend(self, mock_apply):
        """Calling loop() with current last_water_temp should not
        flatten the history."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        loop(estia_optimizer.last_water_temp)

        self.assertEqual(estia_optimizer.last_last_water_temp, 25.0)
        self.assertEqual(estia_optimizer.last_water_temp, 26.0)

    @patch('estia_optimizer.apply_thermostats')
    def test_loop_reeval_repeated_does_not_break_trend(self, mock_apply):
        """Multiple rapid re-evals should not corrupt water temp history."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        for _ in range(10):
            loop(estia_optimizer.last_water_temp)

        self.assertEqual(estia_optimizer.last_last_water_temp, 25.0)
        self.assertEqual(estia_optimizer.last_water_temp, 26.0)

    @patch('estia_optimizer.apply_thermostats')
    def test_loop_reeval_then_real_temp_detects_trend(self, mock_apply):
        """After a re-eval, a real water temp update should still
        detect the upward trend and start boosting."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        loop(estia_optimizer.last_water_temp)
        mock_apply.assert_not_called()

        loop(27.0)
        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_loop_real_temp_still_shifts_history(self, mock_apply):
        """A real new water temp value should shift the history."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0)

        loop(27.0)

        self.assertEqual(estia_optimizer.last_last_water_temp, 26.0)
        self.assertEqual(estia_optimizer.last_water_temp, 27.0)

    # --- Termostat1NP immediate apply tests ---

    @patch('estia_optimizer.apply_thermostats')
    def test_termostat_change_while_boosting_applies_immediately(
            self, mock_apply):
        """Changing Termostat1NP while boosting should call
        apply_thermostats immediately."""
        self._reset_globals(boosting=True)
        estia_optimizer.termostat_temp_1np = 21.0

        # Simulate what the MQTT handler does
        estia_optimizer.termostat_temp_1np = 22.0
        estia_optimizer.apply_thermostats()

        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_termostat_change_while_not_boosting_applies_immediately(
            self, mock_apply):
        """Changing Termostat1NP while not boosting should call
        apply_thermostats immediately."""
        self._reset_globals(boosting=False)
        estia_optimizer.termostat_temp_1np = 21.0

        estia_optimizer.termostat_temp_1np = 22.0
        estia_optimizer.apply_thermostats()

        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_repeated_same_water_temp_no_state_corruption(self, mock_apply):
        """Repeated same water temp should not change boosting state."""
        self._reset_globals(last_last=25.0, last=26.0, target=30.0,
                            boosting=False)

        for _ in range(5):
            loop(26.0)

        self.assertFalse(estia_optimizer.is_boosting)
        self.assertEqual(estia_optimizer.last_last_water_temp, 25.0)
        self.assertEqual(estia_optimizer.last_water_temp, 26.0)
        mock_apply.assert_not_called()


if __name__ == '__main__':
    unittest.main()
