import asyncio
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock


class LoopBreak(Exception):
    """Raised by mocked sleep to break out of while True loops."""
    pass


# Mock hardware/unavailable modules before any test imports them.
# yr.py needs metno_locationforecast (may not be installed in all envs)
# co2.py needs seeed_sgp30 and grove (Raspberry Pi hardware libraries)
for _mod in ['metno_locationforecast', 'seeed_sgp30', 'grove', 'grove.i2c']:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# co2.py has module-level asyncio.run() that would start the loop on import.
# Pre-import it with asyncio.run mocked to prevent that.
_orig_asyncio_run = asyncio.run
asyncio.run = MagicMock()
import co2  # noqa: E402
asyncio.run = _orig_asyncio_run


class TestEstiaResilience(unittest.TestCase):
    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_survives_api_error(self, mock_api_cls, mock_mqtt, mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_device_detail = AsyncMock(
            side_effect=Exception("API timeout")
        )

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        mock_sleep.assert_called_with(60)

    @patch('estia.time.sleep', side_effect=[None, LoopBreak])
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_recovers_after_error(self, mock_api_cls, mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_device_detail = AsyncMock(side_effect=[
            Exception("API timeout"),
            {
                "ACStateData": "0c" + "80" + "00" + "00" + "03" + "00"
                               + "80" + "80" + "00" + "00" + "00" + "00"
                               + "00" + "80" + "80" + "00" + "00",
                "TWI_Temp": "80",
                "TWO_Temp": "80",
                "TO_Temp": "80",
            }
        ])

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        self.assertEqual(mock_sleep.call_count, 2)
        self.assertTrue(mock_client.publish.called)


class TestInverterResilience(unittest.TestCase):
    @patch('inverter.time.sleep', side_effect=LoopBreak)
    @patch('inverter.goodwe.connect', new_callable=AsyncMock)
    @patch('inverter.connect_mqtt')
    def test_survives_read_error(self, mock_mqtt, mock_gw, mock_sleep):
        mock_client = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_inverter = AsyncMock()
        mock_gw.return_value = mock_inverter
        mock_inverter.read_runtime_data = AsyncMock(
            side_effect=Exception("inverter unreachable")
        )

        import inverter
        with self.assertRaises(LoopBreak):
            asyncio.run(inverter.publish(mock_client))

        mock_sleep.assert_called()

    @patch('inverter.time.sleep', side_effect=[None, LoopBreak])
    @patch('inverter.goodwe.connect', new_callable=AsyncMock)
    @patch('inverter.connect_mqtt')
    def test_recovers_after_error(self, mock_mqtt, mock_gw, mock_sleep):
        mock_client = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_inverter = AsyncMock()
        mock_gw.return_value = mock_inverter
        runtime_data = {
            "ppv1": 1, "ppv2": 2, "ppv": 3,
            "house_consumption": 100, "pbattery1": 50,
            "igrid": 1, "igrid2": 2, "igrid3": 3,
            "apparent_power": 100, "reactive_power": 50,
            "active_power": 80, "meter_active_power_total": 90,
            "total_inverter_power": 100,
            "temperature_air": 30, "temperature": 40,
            "e_bat_charge_total": 10, "e_bat_discharge_total": 5,
            "e_bat_charge_day": 2, "e_bat_discharge_day": 1,
            "e_day": 15, "e_load_day": 12,
            "battery_soc": 80, "battery_soh": 95,
            "load_p1": 100, "load_p2": 100, "load_p3": 100,
            "backup_i1": 0, "backup_i2": 0, "backup_i3": 0,
            "diagnose_result_label": "",
        }
        mock_inverter.read_runtime_data = AsyncMock(side_effect=[
            Exception("inverter unreachable"),
            runtime_data,
        ])

        import inverter
        with self.assertRaises(LoopBreak):
            asyncio.run(inverter.publish(mock_client))

        self.assertEqual(mock_sleep.call_count, 2)
        self.assertTrue(mock_client.publish.called)


class TestNetatmoResilience(unittest.TestCase):
    @patch('netatmo.time.sleep', side_effect=LoopBreak)
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_survives_update_error(self, mock_mqtt, mock_read,
                                   mock_oauth, mock_home, mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_home_instance = MagicMock()
        mock_home.return_value = mock_home_instance
        mock_home_instance.update.side_effect = Exception("API error")

        import netatmo
        with self.assertRaises(LoopBreak):
            asyncio.run(netatmo.main())

        mock_sleep.assert_called_with(60)

    @patch('netatmo.time.sleep', side_effect=[None, LoopBreak])
    @patch('netatmo.pyatmo.HomeStatus')
    @patch('netatmo.pyatmo.NetatmoOAuth2')
    @patch('netatmo.read_string_from_file', return_value="fake_token")
    @patch('netatmo.connect_mqtt')
    def test_recovers_after_error(self, mock_mqtt, mock_read,
                                  mock_oauth, mock_home, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_home_instance = MagicMock()
        mock_home.return_value = mock_home_instance

        room_data = {
            'therm_measured_temperature': 21.5,
            'heating_power_request': 50,
        }
        mock_home_instance.update.side_effect = [
            Exception("API error"),
            None,
        ]
        mock_home_instance.rooms.get.return_value = room_data

        import netatmo
        with self.assertRaises(LoopBreak):
            asyncio.run(netatmo.main())

        self.assertEqual(mock_sleep.call_count, 2)
        self.assertTrue(mock_client.publish.called)


class TestRehauResilience(unittest.TestCase):
    @patch('rehau.time.sleep', side_effect=LoopBreak)
    @patch('rehau.requests.get', side_effect=Exception("connection refused"))
    @patch('rehau.connect_mqtt')
    def test_survives_request_error(self, mock_mqtt, mock_get, mock_sleep):
        mock_mqtt.return_value = MagicMock()

        import rehau
        with self.assertRaises(LoopBreak):
            asyncio.run(rehau.main())

        mock_sleep.assert_called_with(60)


class TestYrResilience(unittest.TestCase):
    @patch('yr.ttime.sleep', side_effect=LoopBreak)
    @patch('yr.forecast')
    def test_survives_forecast_error(self, mock_forecast, mock_sleep):
        mock_forecast.update.side_effect = Exception("network error")

        import yr
        with self.assertRaises(LoopBreak):
            yr.publish(MagicMock())

        mock_sleep.assert_called_with(1800)


class TestCo2Resilience(unittest.TestCase):
    @patch('co2.time.sleep', side_effect=LoopBreak)
    @patch('co2.connect_mqtt')
    @patch('co2.seeed_sgp30.grove_sgp30')
    def test_survives_sensor_error(self, mock_sgp30_cls, mock_mqtt,
                                   mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_sgp30 = MagicMock()
        mock_sgp30_cls.return_value = mock_sgp30
        mock_sgp30.read_measurements.side_effect = Exception("I2C error")

        with self.assertRaises(LoopBreak):
            asyncio.run(co2.store_runtime_data())

        mock_sleep.assert_called_with(5)


class TestCarResilience(unittest.TestCase):
    @patch('car.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('car.carconnectivity.CarConnectivity')
    @patch('car.connect_mqtt')
    def test_survives_vehicle_error(self, mock_mqtt, mock_cc_cls,
                                    mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        mock_garage = MagicMock()
        mock_cc.get_garage.return_value = mock_garage
        mock_garage.list_vehicles.side_effect = Exception("API error")

        import car
        with self.assertRaises(LoopBreak):
            asyncio.run(car.main())

        mock_sleep.assert_called_with(120)

    @patch('car.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('car.carconnectivity.CarConnectivity')
    @patch('car.connect_mqtt')
    def test_cleanup_runs_after_error(self, mock_mqtt, mock_cc_cls,
                                      mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        mock_garage = MagicMock()
        mock_cc.get_garage.return_value = mock_garage
        mock_garage.list_vehicles.side_effect = Exception("API error")

        import car
        with self.assertRaises(LoopBreak):
            asyncio.run(car.main())

        mock_cc.shutdown.assert_called_once()


class TestSkodaResilience(unittest.TestCase):
    @patch('skoda.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('skoda.carconnectivity.CarConnectivity')
    @patch('skoda.connect_mqtt')
    def test_survives_fetch_error(self, mock_mqtt, mock_cc_cls, mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        mock_cc.fetch_all.side_effect = [None, Exception("network error")]

        import skoda
        with self.assertRaises(LoopBreak):
            asyncio.run(skoda.main())

        mock_sleep.assert_called_with(120)

    @patch('skoda.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('skoda.carconnectivity.CarConnectivity')
    @patch('skoda.connect_mqtt')
    def test_cleanup_runs_after_error(self, mock_mqtt, mock_cc_cls,
                                      mock_sleep):
        mock_mqtt.return_value = MagicMock()
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        mock_cc.fetch_all.side_effect = [None, Exception("network error")]

        import skoda
        with self.assertRaises(LoopBreak):
            asyncio.run(skoda.main())

        mock_cc.shutdown.assert_called_once()


if __name__ == '__main__':
    unittest.main()
