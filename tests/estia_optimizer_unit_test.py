import io
import unittest
from unittest.mock import patch, MagicMock

import requests

import common
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


class TestResubscribe(unittest.TestCase):
    """Change 020, D9: estia_optimizer subscribes again after an MQTT reconnect."""

    TOPICS = ['bool/estia/heating_compressor_active', 'home/rehau_set/#', 'command/Termostat1NP']

    def test_subscribes_on_each_connect(self):
        client = common.new_client("test020-estia_optimizer")
        client.subscribe = MagicMock()
        estia_optimizer.subscribe(client, self.TOPICS)
        self.assertEqual(client.subscribe.call_count, 0)
        with patch("sys.stdout", new_callable=io.StringIO):
            client.on_connect(client, None, {}, 0, None)
            client.on_connect(client, None, {}, 0, None)
        self.assertEqual([c.args[0] for c in client.subscribe.call_args_list], self.TOPICS * 2)


class TestRehauPost(unittest.TestCase):
    """Change 020: the Rehau POST has a 10 s timeout, and a failure writes one ERROR."""

    def setUp(self):
        estia_optimizer.is_boosting = False
        estia_optimizer.termostat_temp_1np = 21.0
        self._reset_rooms()
        self.addCleanup(self._reset_rooms)
        fresh = patch.object(estia_optimizer, "rehau_log", common.ConnectionLog(estia_optimizer.log, "Rehau"))
        fresh.start()
        self.addCleanup(fresh.stop)

    @staticmethod
    def _reset_rooms():
        for room in estia_optimizer.rooms:
            room.currentTemp = 0

    def _apply(self):
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            estia_optimizer.apply_thermostats(include_netatmo=False)
        return out.getvalue()

    @patch("estia_optimizer.requests.post")
    def test_post_timeout(self, post):
        post.return_value = MagicMock(status_code=200)
        out = self._apply()
        self.assertEqual(post.call_count, 7)
        for call in post.call_args_list:
            self.assertEqual(call.kwargs.get("timeout"), 10)
        self.assertNotIn("ERROR", out)

    @patch("estia_optimizer.requests.post")
    def test_http_500_is_error(self, post):
        post.return_value = MagicMock(status_code=500)
        out = self._apply()
        self.assertEqual(out.count("ERROR estia_optimizer:"), 1)
        self.assertIn("HTTP 500", out)

    @patch("estia_optimizer.requests.post", side_effect=requests.Timeout("read timed out"))
    def test_timeout_is_error(self, post):
        out = self._apply()
        self.assertEqual(out.count("ERROR estia_optimizer:"), 1)


if __name__ == '__main__':
    unittest.main()
