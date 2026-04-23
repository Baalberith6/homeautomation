import unittest
from unittest.mock import patch, MagicMock

import estia_optimizer


class TestEstiaOptimizer(unittest.TestCase):

    def setUp(self):
        estia_optimizer.is_boosting = False
        estia_optimizer.termostat_temp_1np = 21.0

    @patch('estia_optimizer.apply_thermostats')
    def test_compressor_active_starts_boosting(self, mock_apply):
        estia_optimizer.is_boosting = False

        msg = MagicMock()
        msg.topic = "bool/estia/heating_compressor_active"
        msg.payload.decode.return_value = "True"

        # Get the on_message handler
        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_compressor_inactive_stops_boosting(self, mock_apply):
        estia_optimizer.is_boosting = True

        msg = MagicMock()
        msg.topic = "bool/estia/heating_compressor_active"
        msg.payload.decode.return_value = "False"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()

    @patch('estia_optimizer.apply_thermostats')
    def test_compressor_active_when_already_boosting_does_nothing(
            self, mock_apply):
        estia_optimizer.is_boosting = True

        msg = MagicMock()
        msg.topic = "bool/estia/heating_compressor_active"
        msg.payload.decode.return_value = "True"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_compressor_inactive_when_not_boosting_does_nothing(
            self, mock_apply):
        estia_optimizer.is_boosting = False

        msg = MagicMock()
        msg.topic = "bool/estia/heating_compressor_active"
        msg.payload.decode.return_value = "False"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        self.assertFalse(estia_optimizer.is_boosting)
        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_termostat_change_while_boosting(self, mock_apply):
        estia_optimizer.is_boosting = True
        estia_optimizer.termostat_temp_1np = 21.0

        msg = MagicMock()
        msg.topic = "command/Termostat1NP"
        msg.payload.decode.return_value = "22.0"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
            "command/Termostat1NP",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        self.assertEqual(estia_optimizer.termostat_temp_1np, 22.0)
        mock_apply.assert_called_once_with(include_netatmo=False)

    @patch('estia_optimizer.apply_thermostats')
    def test_termostat_same_value_does_nothing(self, mock_apply):
        estia_optimizer.termostat_temp_1np = 21.0

        msg = MagicMock()
        msg.topic = "command/Termostat1NP"
        msg.payload.decode.return_value = "21.0"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
            "command/Termostat1NP",
        ])
        on_message = client.on_message

        on_message(client, None, msg)

        mock_apply.assert_not_called()

    @patch('estia_optimizer.apply_thermostats')
    def test_repeated_compressor_active_only_boosts_once(self, mock_apply):
        estia_optimizer.is_boosting = False

        msg = MagicMock()
        msg.topic = "bool/estia/heating_compressor_active"
        msg.payload.decode.return_value = "True"

        client = MagicMock()
        estia_optimizer.subscribe(client, [
            "bool/estia/heating_compressor_active",
        ])
        on_message = client.on_message

        for _ in range(5):
            on_message(client, None, msg)

        self.assertTrue(estia_optimizer.is_boosting)
        mock_apply.assert_called_once()


if __name__ == '__main__':
    unittest.main()
