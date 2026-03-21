import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import netatmo


class LoopBreak(Exception):
    pass


class TestFileIO(unittest.TestCase):
    def setUp(self):
        self._orig_file_path = netatmo.file_path
        fd, self.tmp_path = tempfile.mkstemp(suffix='.token')
        os.close(fd)
        netatmo.file_path = self.tmp_path

    def tearDown(self):
        netatmo.file_path = self._orig_file_path
        if os.path.exists(self.tmp_path):
            os.unlink(self.tmp_path)

    def test_save_writes_refresh_token(self):
        netatmo.save_string_to_file({'refresh_token': 'abc123'})
        with open(self.tmp_path) as f:
            self.assertEqual('abc123', f.read())

    def test_save_only_writes_token_not_whole_dict(self):
        netatmo.save_string_to_file({
            'refresh_token': 'the_token',
            'access_token': 'should_not_appear',
        })
        with open(self.tmp_path) as f:
            content = f.read()
        self.assertEqual('the_token', content)

    def test_read_returns_content(self):
        with open(self.tmp_path, 'w') as f:
            f.write('my_token')
        self.assertEqual('my_token', netatmo.read_string_from_file())

    def test_read_strips_whitespace(self):
        with open(self.tmp_path, 'w') as f:
            f.write('  token_with_spaces  \n')
        self.assertEqual('token_with_spaces',
                         netatmo.read_string_from_file())

    def test_read_missing_file_returns_none(self):
        netatmo.file_path = '/tmp/nonexistent_netatmo_token_file_12345'
        self.assertIsNone(netatmo.read_string_from_file())

    def test_roundtrip_save_then_read(self):
        netatmo.save_string_to_file({'refresh_token': 'roundtrip_token'})
        self.assertEqual('roundtrip_token',
                         netatmo.read_string_from_file())


class TestHeatingPowerNormalization(unittest.TestCase):
    """Verify heating_power_request is divided by 100 before publishing."""

    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake")
    @patch('netatmo.connect_mqtt')
    def test_full_power_published_as_1(self, mock_mqtt, mock_read,
                                       mock_oauth, mock_home, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        home = MagicMock()
        mock_home.return_value = home
        home.rooms.get.return_value = {
            'therm_measured_temperature': 22.0,
            'heating_power_request': 100,
        }

        with self.assertRaises(LoopBreak):
            asyncio.run(netatmo.main())

        on_calls = [
            call for call in mock_client.publish.call_args_list
            if "home/netatmo/on/" in call[0][0]
        ]
        # All 7 rooms should publish 1.0 (100/100)
        for call in on_calls:
            self.assertEqual(1.0, call[0][1])

    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake")
    @patch('netatmo.connect_mqtt')
    def test_zero_power_published_as_0(self, mock_mqtt, mock_read,
                                       mock_oauth, mock_home, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        home = MagicMock()
        mock_home.return_value = home
        home.rooms.get.return_value = {
            'therm_measured_temperature': 18.0,
            'heating_power_request': 0,
        }

        with self.assertRaises(LoopBreak):
            asyncio.run(netatmo.main())

        on_calls = [
            call for call in mock_client.publish.call_args_list
            if "home/netatmo/on/" in call[0][0]
        ]
        for call in on_calls:
            self.assertEqual(0.0, call[0][1])

    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake")
    @patch('netatmo.connect_mqtt')
    def test_all_seven_rooms_published(self, mock_mqtt, mock_read,
                                       mock_oauth, mock_home, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        home = MagicMock()
        mock_home.return_value = home
        home.rooms.get.return_value = {
            'therm_measured_temperature': 20.0,
            'heating_power_request': 50,
        }

        with self.assertRaises(LoopBreak):
            asyncio.run(netatmo.main())

        temp_topics = [
            call[0][0] for call in mock_client.publish.call_args_list
            if "home/netatmo/temp_curr/" in call[0][0]
        ]
        expected_rooms = {"hala", "kupelna", "chodba", "hostovska",
                          "julinka", "kubo", "spalna"}
        actual_rooms = {t.split("/")[-1] for t in temp_topics}
        self.assertEqual(expected_rooms, actual_rooms)


# NOTE: netatmo.py has a likely bug — tokenRefresher is initialized to 0
# but never incremented inside the loop, so the token refresh condition
# (tokenRefresher > 120) is never triggered. The token only gets refreshed
# once during startup. A fix would add tokenRefresher += 1 to the loop body.


if __name__ == '__main__':
    unittest.main()
