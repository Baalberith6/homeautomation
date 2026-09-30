import asyncio
import io
import sys
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Mock heavy external dependencies that may not be installed locally
for _mod in ('influxdb_client', 'influxdb_client.client',
             'influxdb_client.client.write_api'):
    sys.modules.setdefault(_mod, MagicMock())

import common  # noqa: E402
import estia_energy  # noqa: E402
from estia_energy import calculate_cop, merge_arrays
from estia_energy import replace_two_highest_with


class TestEstiaEnergy(unittest.TestCase):

    def test(self):
        self.assertEqual((0,0), calculate_cop([0, 0, 0], [18,18,18]))
        self.assertEqual((12.87, 200), calculate_cop([1287], [0]))
        self.assertEqual((6.2979274611398965, 772), calculate_cop([1287, 572], [0, 2]))
        self.assertEqual((6.563934426229508, 915), calculate_cop([1287, 572, 143], [0, 2, 10]))
        self.assertEqual((3.8573409040631232, 13561), calculate_cop([577, 1122, 26, 902, 1138, 411, 551, 1004, 119, 805, 595, 1046, 1042, 178, 266, 526, 195, 657, 1526, 25, 573, 589, 143, 871], [0.7, 0.7, 1, 0.9, 1.7, 1.7, 1.7, 1.9, 2.2, 2.9, 3.7, 4.4, 5, 4.6, 4.9, 4.2, 3.9, 3.7, 3.4, 3.2, 2.8, 2.4, 2.2, 2.4])) # 1.1.2024

        self.assertEqual([572, 957, 1109, 122, 1010, 1115, 841, 26, 752, 308, 26, 758, 200, 308, 1061, 1082, 212, 1035, 998, 441, 769, 1123, 691, 26],
                         replace_two_highest_with([572, 957, 1109, 122, 1010, 1115, 841, 26, 752, 308, 26, 758, 2483, 308, 1061, 1082, 212, 1035, 998, 441, 769, 1123, 691, 26], 200))
        self.assertEqual([572, 957, 1109, 122, 1010, 1115, 841, 26, 752, 308, 26, 758, 2483, 333, 1061, 1082, 212, 1035, 998, 441, 769, 1123, 691, 26],
                         merge_arrays([572, 957, 1109, 122, 1010, 1115, 841, 26, 752, 308, 26, 758, 2483, 308, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 333, 1061, 1082, 212, 1035, 998, 441, 769, 1123, 691, 26]))
        # TUV 2x day
        # self.assertEqual((12.155, 400), calculate_cop([1287, 572], [0, 2]))
        # self.assertEqual((11.060773480662984, 543), calculate_cop([1287, 572, 143], [0, 2, 10]))
        # self.assertEqual((4.143975283213182, 12623), calculate_cop([577, 1122, 26, 902, 1138, 411, 551, 1004, 119, 805, 595, 1046, 1042, 178, 266, 526, 195, 657, 1526, 25, 573, 589, 143, 871], [0.7, 0.7, 1, 0.9, 1.7, 1.7, 1.7, 1.9, 2.2, 2.9, 3.7, 4.4, 5, 4.6, 4.9, 4.2, 3.9, 3.7, 3.4, 3.2, 2.8, 2.4, 2.2, 2.4])) # 1.1.2024
        # self.assertEqual((3.45949184840144, 23615), calculate_cop([1111, 1244, 1564, 1490, 1512, 1430, 1418, 1407, 1494, 1262, 167, 1379, 1841, 514, 26, 776, 340, 267, 1692, 1171, 1126, 1216, 1171, 1130], [-10, -10.7, -10.8, -10.6, -11.1, -10.8, -10.5, -10.1, -5.8, -2.7, -2.3, -1.1, -0.5, -0.1, -0.5, -1.2, -2.2, -2.8, -4.4, -5.7, -6.8, -6.9, -6.5, -5.2])) # 21.1.2024

def _day():
    return [{"EnergyConsumption": [{"Energy": 100}] * 24}]


def _at(minute):
    return datetime(2026, 9, 29, 10, minute)


class TestTick(unittest.TestCase):
    """Change 019: the COP loop logs in again under the backoff."""

    def setUp(self):
        import estia_energy
        from estia_api import LoginBackoff
        self.ee = estia_energy
        self.backoff = LoginBackoff()
        self.state = estia_energy.new_state()
        self.api = AsyncMock()
        self.write = patch.object(estia_energy, "write_api", MagicMock())
        self.mock_write = self.write.start()
        self.debug = patch.dict(estia_energy.c, {"debug": False})
        self.debug.start()

    def tearDown(self):
        self.write.stop()
        self.debug.stop()

    def _tick(self, minute, mono):
        asyncio.run(self.ee.tick(self.api, self.state, self.backoff,
                                 _at(minute), mono))

    def test_failed_call_retried_once(self):
        from estia_api import ToshibaAcHttpApiError
        self.api.get_hourly_consumption = AsyncMock(side_effect=[
            ToshibaAcHttpApiError("HTTP 401: token expired"),
            _day(), _day(),
        ])
        self._tick(22, 1000)
        self.assertEqual(self.mock_write.write.call_count, 0)
        self._tick(23, 1060)
        self.assertEqual(self.api.connect.await_count, 2)
        self.assertEqual(self.mock_write.write.call_count, 2)
        self._tick(24, 1120)
        self.assertEqual(self.mock_write.write.call_count, 2)
        self.assertEqual(self.api.get_hourly_consumption.await_count, 3)

    def test_error_printed_without_debug(self):
        from estia_api import ToshibaAcHttpApiRateLimitError
        self.api.connect = AsyncMock(side_effect=ToshibaAcHttpApiRateLimitError(
            "HTTP 429: Too many requests. Try again in 60 seconds."))
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            self._tick(22, 1000)
        self.assertIn("Toshiba error: HTTP 429: Too many requests. "
                      "Try again in 60 seconds.; next login in 60 s",
                      out.getvalue())

    def test_waits_for_backoff(self):
        from estia_api import ToshibaAcHttpApiError
        self.api.connect = AsyncMock(
            side_effect=[ToshibaAcHttpApiError("HTTP 500: x"), None])
        self._tick(22, 1000)
        self._tick(22, 1030)
        self.assertEqual(self.api.connect.await_count, 1)
        self.assertEqual(self.api.get_hourly_consumption.await_count, 0)

    def test_influx_error_does_not_log_in(self):
        self.api.get_hourly_consumption = AsyncMock(return_value=_day())
        self.mock_write.write.side_effect = RuntimeError("influx down")
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            self._tick(22, 1000)
            self._tick(23, 1060)
        self.assertIn("InfluxDB error: influx down", out.getvalue())
        self.assertEqual(self.api.connect.await_count, 1)
        self.assertEqual(self.api.get_hourly_consumption.await_count, 2)


class TestForgetTokenEnergy(unittest.TestCase):
    """Change 019 revision 2: the Device-ID, the token file, and when to forget the token."""

    def setUp(self):
        import estia_energy
        from estia_api import LoginBackoff
        self.ee = estia_energy
        self.backoff = LoginBackoff()
        self.state = estia_energy.new_state()
        self.api = AsyncMock()
        self.api.forget_token = MagicMock()
        self.write = patch.object(estia_energy, "write_api", MagicMock())
        self.write.start()
        self.debug = patch.dict(estia_energy.c, {"debug": False})
        self.debug.start()

    def tearDown(self):
        self.write.stop()
        self.debug.stop()

    def _tick(self, minute, mono):
        with patch("sys.stdout", new_callable=io.StringIO):
            asyncio.run(self.ee.tick(self.api, self.state, self.backoff, _at(minute), mono))

    def test_client_gets_device_id_and_token_path(self):
        import estia_energy
        from config import generalConfig
        name = ("toshiba_token_estia_energy.dev.json" if generalConfig["debug"]
                else "toshiba_token_estia_energy.json")
        self.assertEqual(estia_energy.api.device_id, "14c2a40d2951f0e0")
        self.assertEqual(estia_energy.api.token_path, name)

    def test_auth_error_forgets_token(self):
        from estia_api import ToshibaAcHttpApiAuthError
        self.api.get_hourly_consumption = AsyncMock(side_effect=ToshibaAcHttpApiAuthError("HTTP 401: "))
        self._tick(22, 1000)
        self.assertEqual(self.api.forget_token.call_count, 1)

    def test_generic_error_keeps_token(self):
        from estia_api import ToshibaAcHttpApiError
        self.api.get_hourly_consumption = AsyncMock(side_effect=ToshibaAcHttpApiError("HTTP 500: x"))
        self._tick(22, 1000)
        self.assertEqual(self.api.forget_token.call_count, 0)

    def test_fourth_failure_forgets_token(self):
        from estia_api import ToshibaAcHttpApiError
        self.api.get_hourly_consumption = AsyncMock(side_effect=ToshibaAcHttpApiError("HTTP 500: x"))
        for minute, mono in ((22, 1000), (23, 1060), (28, 1360)):
            self._tick(minute, mono)
        self.assertEqual(self.api.forget_token.call_count, 0)
        self._tick(38, 1960)
        self.assertEqual(self.api.forget_token.call_count, 1)


class TestResubscribe(unittest.TestCase):
    """Change 020, D9: estia_energy subscribes again after an MQTT reconnect."""

    TOPICS = ['jsons/weather/local/temps_24h']

    def test_subscribes_on_each_connect(self):
        client = common.new_client("test020-estia_energy")
        client.subscribe = MagicMock()
        estia_energy.subscribe(client, self.TOPICS)
        self.assertEqual(client.subscribe.call_count, 0)
        with patch("sys.stdout", new_callable=io.StringIO):
            client.on_connect(client, None, {}, 0, None)
            client.on_connect(client, None, {}, 0, None)
        self.assertEqual([c.args[0] for c in client.subscribe.call_args_list], self.TOPICS * 2)


class TestFreshSession(unittest.TestCase):
    """Change 019 revision 3: each Toshiba try of the COP loop starts with a new HTTP session.

    On 2026-09-30 the first call of the old session after an idle hour got the gateway's 403,
    while the same token worked from a new session.
    """

    def setUp(self):
        import estia_energy
        from estia_api import LoginBackoff
        self.ee = estia_energy
        self.backoff = LoginBackoff()
        self.state = estia_energy.new_state()
        self.api = AsyncMock()
        self.api.forget_token = MagicMock()
        write = patch.object(estia_energy, "write_api", MagicMock())
        write.start()
        self.addCleanup(write.stop)
        debug = patch.dict(estia_energy.c, {"debug": False})
        debug.start()
        self.addCleanup(debug.stop)

    def _tick(self, minute, mono):
        with patch("sys.stdout", new_callable=io.StringIO):
            asyncio.run(self.ee.tick(self.api, self.state, self.backoff, _at(minute), mono))

    def test_new_session_before_the_calls(self):
        self.api.get_hourly_consumption = AsyncMock(return_value=_day())
        self._tick(22, 1000)
        names = [c[0] for c in self.api.mock_calls]
        self.assertEqual(names[0], "reset_session", names)
        self.assertIn("get_hourly_consumption", names)

    def test_no_new_session_when_nothing_is_due(self):
        self.state["logged_in"] = True
        self._tick(30, 1000)
        self.api.reset_session.assert_not_awaited()

if __name__ == '__main__':
    unittest.main()
