import io
import unittest
from datetime import datetime
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



class TestNightSetback(unittest.TestCase):
    """Change 024: the ground floor drops 1 C at night; the boost is +1 C on both floors."""

    def setUp(self):
        estia_optimizer.is_boosting = False
        estia_optimizer.termostat_temp_1np = 21.0
        estia_optimizer.applied_is_day = None
        self._reset_rooms()
        self.addCleanup(self._reset_state)
        self.clock = patch.object(estia_optimizer, "_now", return_value=datetime(2026, 10, 22, 12, 0))
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        fresh = patch.object(estia_optimizer, "rehau_log", common.ConnectionLog(estia_optimizer.log, "Rehau"))
        fresh.start()
        self.addCleanup(fresh.stop)

    @staticmethod
    def _reset_rooms():
        for room in estia_optimizer.rooms:
            room.currentTemp = 0

    def _reset_state(self):
        estia_optimizer.is_boosting = False
        estia_optimizer.termostat_temp_1np = 21.0
        estia_optimizer.applied_is_day = None
        self._reset_rooms()

    def _at(self, hour, minute=0):
        self.now.return_value = datetime(2026, 10, 22, hour, minute)

    @staticmethod
    def _send(topic, payload):
        msg = MagicMock()
        msg.topic = topic
        msg.payload.decode.return_value = payload
        client = MagicMock()
        estia_optimizer.subscribe(client, [topic])
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            client.on_message(client, None, msg)
        return out.getvalue()

    def test_is_day_boundaries(self):
        self.assertTrue(estia_optimizer.is_day(7))
        self.assertTrue(estia_optimizer.is_day(18))
        self.assertFalse(estia_optimizer.is_day(19))
        self.assertFalse(estia_optimizer.is_day(6))
        self.assertFalse(estia_optimizer.is_day(0))

    def test_setpoints_table(self):
        sp = estia_optimizer.setpoints
        self.assertEqual(sp(21.0, True, False), (21.0, 21.0))
        self.assertEqual(sp(21.0, True, True), (22.0, 22.0))
        self.assertEqual(sp(21.0, False, False), (20.0, 21.0))
        self.assertEqual(sp(21.0, False, True), (21.0, 22.0))

    @patch("estia_optimizer.read_string_from_file", return_value="token")
    @patch("estia_optimizer.pyatmo")
    @patch("estia_optimizer.requests.post")
    def test_apply_sends_night_boost_values(self, post, pyatmo, _token):
        post.return_value = MagicMock(status_code=200)
        self._at(23)
        estia_optimizer.is_boosting = True
        with patch("sys.stdout", new_callable=io.StringIO):
            estia_optimizer.apply_thermostats()
        self.assertEqual(post.call_count, 7)
        for call in post.call_args_list:
            self.assertEqual(call.kwargs["data"]["RSH"], 21.0)
            self.assertEqual(call.kwargs["data"]["temp"], estia_optimizer.calc_rehau_temp(21.0))
        thermpoint = pyatmo.HomeStatus.return_value.set_room_thermpoint
        self.assertEqual(thermpoint.call_count, 7)
        for call in thermpoint.call_args_list:
            self.assertEqual(call.kwargs["temp"], 22.0)

    @patch("estia_optimizer.apply_thermostats")
    def test_window_change_on_termostat_message(self, mock_apply):
        estia_optimizer.applied_is_day = True
        self._at(19)
        self._send("command/Termostat1NP", "21.0")
        mock_apply.assert_called_once_with(include_netatmo=False)
        self._send("command/Termostat1NP", "21.0")
        mock_apply.assert_called_once_with(include_netatmo=False)

    @patch("estia_optimizer.apply_thermostats")
    def test_window_change_on_compressor_message(self, mock_apply):
        estia_optimizer.applied_is_day = False
        self._at(7)
        self._send("bool/estia/heating_compressor_active", "False")
        mock_apply.assert_called_once_with(include_netatmo=False)
        self.assertFalse(estia_optimizer.is_boosting)

    @patch("estia_optimizer.apply_thermostats")
    def test_first_termostat_message_writes_rehau(self, mock_apply):
        estia_optimizer.termostat_temp_1np = None
        self._send("command/Termostat1NP", "21.0")
        mock_apply.assert_called_once_with(include_netatmo=False)
        self._send("command/Termostat1NP", "21.0")
        mock_apply.assert_called_once_with(include_netatmo=False)

    @patch("estia_optimizer.apply_thermostats")
    def test_no_window_write_before_first_termostat(self, mock_apply):
        estia_optimizer.termostat_temp_1np = None
        estia_optimizer.applied_is_day = True
        self._at(20)
        self._send("bool/estia/heating_compressor_active", "False")
        mock_apply.assert_not_called()

    @patch("estia_optimizer.apply_thermostats")
    def test_window_change_while_boosting(self, mock_apply):
        estia_optimizer.is_boosting = True
        estia_optimizer.applied_is_day = True
        self._at(19)
        self._send("bool/estia/heating_compressor_active", "True")
        mock_apply.assert_called_once_with(include_netatmo=False)
        self.assertTrue(estia_optimizer.is_boosting)
        self.assertFalse(estia_optimizer.applied_is_day)

    @patch("estia_optimizer.apply_thermostats")
    def test_window_change_logs_one_info_line(self, mock_apply):
        estia_optimizer.applied_is_day = True
        self._at(19)
        out = self._send("command/Termostat1NP", "21.0")
        self.assertEqual(out.count("Window day -> night: Rehau base 20.0C"), 1)


if __name__ == '__main__':
    unittest.main()
