"""Change 020: each lost connection writes an ERROR line, also without DEBUG=1.

Spec: ../kb/work/020-failures-visible-automatically/spec.md, section 2 "What writes an ERROR line".
Each loop runs once: a mocked sleep raises LoopBreak. The mocks follow resilience_test.py.
The new names are read inside the tests, so the old tests still run before they exist.
"""
import asyncio
import io
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# The committed secret.py is a stub without the Tuya names. Add them before moes_co2 is imported.
import secret
for _name in ("tuyaApiKey", "tuyaApiSecret", "solcastKey"):
    if not hasattr(secret, _name):
        setattr(secret, _name, "")

for _mod in ['metno_locationforecast', 'goodwe', 'lxml', 'lxml.html',
             'carconnectivity', 'carconnectivity.carconnectivity',
             'carconnectivity.charging', 'carconnectivity.charging_connector',
             'carconnectivity.vehicle']:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
# As in netatmo_unit_test.py: the local pyatmo may lack the classes the tests patch.
import pyatmo  # noqa: E402
for _cls in ('NetatmoOAuth2', 'HomeStatus'):
    if not hasattr(pyatmo, _cls):
        setattr(pyatmo, _cls, MagicMock())
try:
    import tinytuya  # noqa: F401
except ImportError:
    sys.modules['tinytuya'] = MagicMock()

import common  # noqa: E402


class LoopBreak(Exception):
    """Raised by a mocked sleep to leave a while True loop."""


def _fresh(module, attr, name):
    """A new log with the rules of the service's own log (grace, alert_after)."""
    own = getattr(module, attr)
    return patch.object(module, attr, common.ConnectionLog(module.log, name, grace=own.grace,
                                                           alert_after=own.alert_after))


class TestHttpAlertAfter(unittest.TestCase):
    """020 revision 9: every HTTP poll alerts on the third failure in a row."""

    def test_http_logs_use_three(self):
        import estia_energy
        import grafana_setter
        import moes_co2
        import netatmo
        import rehau
        import skoda
        import vw_euda
        import yr
        logs = [rehau.rehau_log, yr.yr_log, skoda.cc_log, skoda.geo_log, moes_co2.tuya_log,
                grafana_setter.api_log, netatmo.api_log, vw_euda.portal_log, estia_energy.cop_log]
        self.assertEqual(common.HTTP_ALERT_AFTER, 3)
        self.assertEqual([log.alert_after for log in logs], [3] * len(logs))


class TestInverterErrors(unittest.TestCase):

    @patch('inverter.time.sleep', side_effect=LoopBreak)
    @patch('inverter.goodwe.connect', new_callable=AsyncMock)
    def test_read_error(self, mock_gw, mock_sleep):
        import inverter
        mock_inverter = AsyncMock()
        mock_gw.return_value = mock_inverter
        mock_inverter.read_runtime_data = AsyncMock(side_effect=Exception("inverter unreachable"))
        with _fresh(inverter, "goodwe_log", "GoodWe"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(inverter.publish(MagicMock()))
        self.assertIn("ERROR inverter: GoodWe failed: inverter unreachable", out.getvalue())

    @patch('inverter.goodwe.connect', new_callable=AsyncMock, side_effect=OSError("no route"))
    def test_connect_error_at_start(self, mock_gw):
        import inverter
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(OSError):
                asyncio.run(inverter.publish(MagicMock()))
        self.assertIn("ERROR inverter: GoodWe connect failed: no route", out.getvalue())


class TestNetatmoErrors(unittest.TestCase):

    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_update_error(self, mock_mqtt, mock_read, mock_oauth, mock_home, mock_sleep):
        import netatmo
        mock_home.return_value.update.side_effect = Exception("API error")
        with _fresh(netatmo, "api_log", "Netatmo"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(netatmo.main())
        self.assertIn("ERROR netatmo: Netatmo failed: API error", out.getvalue())

    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_first_login_error(self, mock_mqtt, mock_read, mock_oauth):
        import netatmo
        mock_oauth.return_value.refresh_tokens.side_effect = Exception("invalid_grant")
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(Exception):
                asyncio.run(netatmo.main())
        self.assertIn("ERROR netatmo: Netatmo login failed: invalid_grant", out.getvalue())


class TestYrErrors(unittest.TestCase):

    @patch('yr.ttime.sleep', side_effect=LoopBreak)
    @patch('yr.forecast')
    def test_forecast_error(self, mock_forecast, mock_sleep):
        import yr
        mock_forecast.update.side_effect = Exception("network error")
        with _fresh(yr, "yr_log", "yr.no"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                yr.publish(MagicMock())
        self.assertIn("WARNING yr: yr.no failed: network error", out.getvalue())
        self.assertNotIn("ERROR", out.getvalue())


class TestSkodaErrors(unittest.TestCase):

    @patch('skoda.asyncio.sleep', new_callable=AsyncMock, side_effect=LoopBreak)
    @patch('skoda.carconnectivity.CarConnectivity')
    @patch('skoda.connect_mqtt')
    def test_fetch_error(self, mock_mqtt, mock_cc_cls, mock_sleep):
        import skoda
        mock_cc_cls.return_value.fetch_all.side_effect = Exception("network error")
        with _fresh(skoda, "cc_log", "CarConnectivity"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(skoda.main())
        self.assertIn("WARNING skoda: CarConnectivity failed: network error", out.getvalue())
        self.assertNotIn("ERROR", out.getvalue())

    def test_geocode_error_is_a_warning(self):
        import skoda
        with _fresh(skoda, "geo_log", "Geocode"), \
                patch("skoda.urllib.request.urlopen", side_effect=Exception("timed out")), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(skoda.get_address(48.1001, 17.1001), "")
        self.assertIn("WARNING skoda: Geocode failed: timed out", out.getvalue())
        self.assertNotIn("ERROR", out.getvalue())


class TestEstiaErrors(unittest.TestCase):

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_api_error(self, mock_api_cls, mock_mqtt, mock_sleep):
        import estia
        mock_api_cls.return_value = AsyncMock()
        mock_api_cls.return_value.get_device_detail = AsyncMock(side_effect=Exception("API timeout"))
        mock_api_cls.return_value.forget_token = MagicMock()
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(estia.main())
        self.assertIn("ERROR estia: Toshiba error: API timeout; next login in 60 s", out.getvalue())


class TestVwEudaErrors(unittest.TestCase):

    @patch('vw_euda.time.sleep', side_effect=LoopBreak)
    @patch('vw_euda.EudaClient')
    @patch('vw_euda.connect_mqtt')
    def test_api_error(self, mock_mqtt, mock_client_cls, mock_sleep):
        import vw_euda
        mock_client_cls.return_value.get_identifier.side_effect = vw_euda.ApiError("GET x -> HTTP 500")
        with _fresh(vw_euda, "portal_log", "EU Data Act portal"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                vw_euda.main()
        self.assertIn("ERROR vw_euda: EU Data Act portal failed: API error: GET x -> HTTP 500", out.getvalue())


class TestVwEudaGrace(unittest.TestCase):
    """020 revision 4: a short portal failure is a WARNING; only 15 min of failure is an ERROR."""

    def test_portal_grace_is_15_min(self):
        import vw_euda
        self.assertEqual(vw_euda.PORTAL_GRACE_S, 15 * 60)
        self.assertEqual(vw_euda.portal_log.grace, vw_euda.PORTAL_GRACE_S)

    @patch('vw_euda.time.sleep', side_effect=LoopBreak)
    @patch('vw_euda.EudaClient')
    @patch('vw_euda.connect_mqtt')
    def test_first_api_error_is_warning(self, mock_mqtt, mock_client_cls, mock_sleep):
        import vw_euda
        mock_client_cls.return_value.get_identifier.side_effect = vw_euda.ApiError("GET x -> HTTP 429")
        fresh = common.ConnectionLog(vw_euda.log, "EU Data Act portal", grace=vw_euda.PORTAL_GRACE_S)
        with patch.object(vw_euda, "portal_log", fresh), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                vw_euda.main()
        self.assertNotIn("ERROR vw_euda", out.getvalue())
        self.assertIn("WARNING vw_euda: EU Data Act portal failed: API error: GET x -> HTTP 429", out.getvalue())


class TestNetatmoRevision5(unittest.TestCase):
    """020 revision 5: the 2 h token refresh runs, and a short Netatmo failure is a WARNING.

    On 2026-09-30 Netatmo failed for one poll at 12:07 (access token expired) and at 18:00
    (MissingTokenError in the refresh); the next poll worked both times.
    """

    def test_netatmo_grace_is_15_min(self):
        import netatmo
        self.assertEqual(netatmo.NETATMO_GRACE_S, 15 * 60)
        self.assertEqual(netatmo.api_log.grace, netatmo.NETATMO_GRACE_S)

    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_first_update_error_is_warning(self, mock_mqtt, mock_read, mock_oauth, mock_home, mock_sleep):
        import netatmo
        mock_home.return_value.update.side_effect = Exception("403 - Forbidden - Access token expired (3)")
        fresh = common.ConnectionLog(netatmo.log, "Netatmo", grace=netatmo.NETATMO_GRACE_S)
        with patch.object(netatmo, "api_log", fresh), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(netatmo.main())
        self.assertNotIn("ERROR netatmo", out.getvalue())
        self.assertIn("WARNING netatmo: Netatmo failed: 403 - Forbidden - Access token expired (3)", out.getvalue())

    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_token_refreshes_every_2_h(self, mock_mqtt, mock_read, mock_oauth, mock_home):
        import netatmo
        mock_home.return_value.rooms.get.return_value = {"therm_measured_temperature": 21.0,
                                                         "heating_power_request": 0}
        sleeps = {"n": 0}

        def sleep(seconds):
            sleeps["n"] += 1
            if sleeps["n"] >= 122:
                raise LoopBreak

        with patch("netatmo.time.sleep", side_effect=sleep), \
                patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(LoopBreak):
                asyncio.run(netatmo.main())
        # Once at the start, and once after 121 polls of 60 s.
        self.assertEqual(mock_oauth.return_value.refresh_tokens.call_count, 2)


class TestVwEudaRelogin(unittest.TestCase):
    """020 revision 5: the hourly re-login after a 401 is an INFO line, not a WARNING."""

    def test_relogin_is_info(self):
        import vw_euda_auth
        client = vw_euda_auth.EudaClient.__new__(vw_euda_auth.EudaClient)
        client._logged_in = True
        client._session = MagicMock()
        client._session.get.side_effect = [MagicMock(status_code=401), MagicMock(status_code=200)]
        client.login = MagicMock(side_effect=lambda: setattr(client, "_logged_in", True))
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            r = client._get("https://example.invalid/list")
        self.assertEqual(r.status_code, 200)
        client.login.assert_called_once()
        self.assertIn("INFO vw_euda: Session expired (401); re-authenticating", out.getvalue())
        self.assertNotIn("WARNING", out.getvalue())


class TestRehauErrors(unittest.TestCase):

    @patch('rehau.time.sleep', side_effect=LoopBreak)
    @patch('rehau.requests.get', side_effect=Exception("connection refused"))
    @patch('rehau.connect_mqtt')
    def test_request_error(self, mock_mqtt, mock_get, mock_sleep):
        import rehau
        with _fresh(rehau, "rehau_log", "Rehau"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(LoopBreak):
                asyncio.run(rehau.main())
        self.assertIn("WARNING rehau: Rehau failed: connection refused", out.getvalue())
        self.assertNotIn("ERROR", out.getvalue())


class TestMoesCo2Errors(unittest.TestCase):

    def test_tuya_error_status(self):
        import moes_co2
        sensor = moes_co2.MOESCo2Sensor("dev020")
        sensor.device = MagicMock()
        sensor.device.getstatus.return_value = {"success": False, "msg": "token invalid"}
        sensor.last_auth_time = time.time()
        with _fresh(moes_co2, "tuya_log", "Tuya cloud"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertIsNone(sensor.get_co2_value())
        self.assertIn("WARNING moes_co2: Tuya cloud failed: ", out.getvalue())
        self.assertIn("token invalid", out.getvalue())
        self.assertNotIn("ERROR", out.getvalue())

    def test_init_failure_exits_with_error(self):
        import moes_co2
        sensor = moes_co2.MOESCo2Sensor("dev020")
        with patch.object(moes_co2, "connect_mqtt", return_value=MagicMock()), \
                patch.object(moes_co2.tinytuya, "Cloud", side_effect=Exception("bad key")), \
                _fresh(moes_co2, "tuya_log", "Tuya cloud"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            sensor.run()
        self.assertIn("WARNING moes_co2: Tuya cloud failed: ", out.getvalue())
        self.assertIn("ERROR moes_co2: Failed to initialize Tuya device, exiting", out.getvalue())


class TestOteForecastErrors(unittest.TestCase):
    """020 revision 7: the cron script oteforecast.py writes one ERROR line and exits 1."""

    @staticmethod
    def _response(hours=24):
        points = [{"x": str(h), "y": 100.0 + h} for h in range(1, hours + 1)]
        return {"data": {"dataLine": [{"title": "Cena (EUR/MWh)", "point": points}]}}

    def test_request_has_timeout(self):
        import oteforecast
        with patch.object(oteforecast.requests, "get") as mock_get:
            oteforecast._request(oteforecast.datetime(2026, 10, 1))
        self.assertEqual(mock_get.call_args.kwargs.get("timeout"), 30)

    def test_failure_is_one_error_line(self):
        import oteforecast
        with patch.object(oteforecast, "run", side_effect=Exception("Failed to resolve 'www.ote-cr.cz'")), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(SystemExit) as ctx:
                oteforecast.main()
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("ERROR oteforecast: OTE forecast failed: Failed to resolve 'www.ote-cr.cz'", out.getvalue())

    def test_success_is_info_line(self):
        import oteforecast
        date = oteforecast.local_tz.localize(oteforecast.datetime(2026, 10, 1))
        with patch.object(oteforecast, "InfluxDBClient"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            oteforecast.send_to_mqtt(self._response(), MagicMock(), date)
        self.assertIn("INFO oteforecast: OTE prices for 2026-10-01: 24 hours written", out.getvalue())


class TestSolarForecastErrors(unittest.TestCase):
    """020 revision 8: solarforecast.py writes one ERROR line, exits 1, and never logs the key."""

    KEY = "solcast-key-020-do-not-log"

    def test_failure_is_one_error_line(self):
        import solarforecast
        with patch.object(solarforecast, "run", side_effect=Exception("Expecting value")), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(SystemExit) as ctx:
                solarforecast.main()
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("ERROR solarforecast: Solcast forecast failed: Expecting value", out.getvalue())

    def test_key_not_in_log_lines(self):
        import solarforecast
        err = solarforecast.requests.HTTPError(
            "429 Client Error: Too Many Requests for url: https://api.solcast.com.au/x?api_key=" + self.KEY)
        with patch.object(solarforecast, "solcastKey", self.KEY), \
                patch.object(solarforecast.requests, "get", side_effect=err), \
                patch("time.sleep"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(SystemExit):
                solarforecast.main()
        text = out.getvalue()
        self.assertIn("WARNING solarforecast: Solcast API attempt 1/3 failed: ", text)
        self.assertIn("ERROR solarforecast: Solcast forecast failed: 429 Client Error", text)
        self.assertIn("api_key=***", text)
        self.assertNotIn(self.KEY, text)

    def test_success_is_info_line(self):
        import solarforecast
        today = solarforecast.datetime.today().strftime("%Y-%m-%d")
        forecasts = [{"pv_estimate": 1.0, "pv_estimate10": 0.5, "pv_estimate90": 1.5,
                      "period_end": f"{today}T{h:02d}:30:00.0000000Z", "period": "PT30M"} for h in (9, 10)]
        with patch.object(solarforecast, "InfluxDBClient"), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            solarforecast.store_runtime_data({"forecasts": forecasts})
        self.assertIn("INFO solarforecast: Solcast forecast: 2 periods written", out.getvalue())


class TestCezBatteryErrors(unittest.TestCase):
    """020 revision 8: cez_battery.py writes one ERROR line and exits 1; the prints are INFO lines."""

    def test_failure_is_one_error_line(self):
        import cez_battery
        with patch.object(cez_battery, "authenticate", side_effect=Exception("Could not find login form")), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            with self.assertRaises(SystemExit) as ctx:
                cez_battery.main()
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("ERROR cez_battery: ČEZ virtual battery failed: Could not find login form", out.getvalue())

    def test_success_is_info_line(self):
        import cez_battery
        data = {"virtualBatteryActualCharge": 895.81, "virtualBatteryAggregatedProduction": 3650.99,
                "virtualBatteryAggregatedConsumption": 2755.18, "virtualBatteryDiscountAmount": 9064.54}
        with patch.object(cez_battery, "authenticate", return_value="t"), \
                patch.object(cez_battery, "fetch_virtual_battery", return_value=data), \
                patch.object(cez_battery, "connect_mqtt", return_value=MagicMock()), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            cez_battery.main()
        self.assertIn("INFO cez_battery: Virtual battery: 895.81 kWh", out.getvalue())
        self.assertIn("INFO cez_battery: Published to MQTT", out.getvalue())


if __name__ == '__main__':
    unittest.main()
