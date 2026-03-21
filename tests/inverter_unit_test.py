import asyncio
import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock


class LoopBreak(Exception):
    pass


BASE_RUNTIME_DATA = {
    "ppv1": 1000, "ppv2": 2000, "ppv": 3000,
    "house_consumption": 500, "pbattery1": 200,
    "igrid": 1.5, "igrid2": 1.6, "igrid3": 1.7,
    "apparent_power": 3100, "reactive_power": 100,
    "active_power": 3000, "meter_active_power_total": 2900,
    "total_inverter_power": 3000,
    "temperature_air": 35, "temperature": 42,
    "e_bat_charge_total": 100, "e_bat_discharge_total": 80,
    "e_bat_charge_day": 5, "e_bat_discharge_day": 3,
    "e_day": 20, "e_load_day": 15,
    "battery_soc": 85, "battery_soh": 97,
    "load_p1": 200, "load_p2": 150, "load_p3": 150,
    "backup_i1": 0.1, "backup_i2": 0.2, "backup_i3": 0.1,
    "diagnose_result_label": "",
}


def _run_one_iteration(diag_label):
    """Run one loop iteration with given diagnose_result_label.

    Returns the mock MQTT client so callers can inspect publishes.
    """
    data = {**BASE_RUNTIME_DATA, "diagnose_result_label": diag_label}
    mock_client = MagicMock()

    with patch('inverter.time.sleep', side_effect=LoopBreak), \
         patch('inverter.goodwe.connect', new_callable=AsyncMock) as mock_gw, \
         patch('inverter.connect_mqtt'):
        mock_inverter = AsyncMock()
        mock_gw.return_value = mock_inverter
        mock_inverter.read_runtime_data = AsyncMock(return_value=data)

        import inverter
        try:
            asyncio.run(inverter.publish(mock_client))
        except LoopBreak:
            pass

    return mock_client


def _get_diag_publish(mock_client):
    """Return the value published to diag/FVE, or None."""
    for call in mock_client.publish.call_args_list:
        if call[0][0] == "diag/FVE":
            return call[0][1]
    return None


class TestDiagnosticsFiltering(unittest.TestCase):
    def test_all_filtered_labels_no_diag_published(self):
        client = _run_one_iteration(
            "Discharge Driver On, Self-use load light"
        )
        self.assertIsNone(_get_diag_publish(client))

    def test_single_filtered_label(self):
        client = _run_one_iteration("Battery Overcharged")
        self.assertIsNone(_get_diag_publish(client))

    def test_all_known_filtered_labels(self):
        label = (
            "Discharge Driver On, Self-use load light, "
            "Battery Overcharged, BMS: Charge disabled, "
            "PF value set, Battery SOC low, "
            "Battery SOC in back, SOC delta too volatile"
        )
        client = _run_one_iteration(label)
        self.assertIsNone(_get_diag_publish(client))

    def test_real_error_passes_through(self):
        client = _run_one_iteration("Grid frequency out of range")
        self.assertEqual("Grid frequency out of range",
                         _get_diag_publish(client))

    def test_mixed_filtered_and_real(self):
        label = "Self-use load light, Grid voltage high, PF value set"
        client = _run_one_iteration(label)
        self.assertEqual("Grid voltage high", _get_diag_publish(client))

    def test_empty_label_no_diag_published(self):
        client = _run_one_iteration("")
        self.assertIsNone(_get_diag_publish(client))

    def test_leading_trailing_commas_stripped(self):
        label = ", Discharge Driver On, Real error, Battery SOC low, "
        client = _run_one_iteration(label)
        self.assertEqual("Real error", _get_diag_publish(client))


class TestWallboxDataExtraction(unittest.TestCase):
    @patch('inverter.time.sleep', side_effect=LoopBreak)
    @patch('inverter.goodwe.connect', new_callable=AsyncMock)
    @patch('inverter.connect_mqtt')
    def test_correct_keys_forwarded(self, mock_mqtt, mock_gw, mock_sleep):
        mock_client = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_inverter = AsyncMock()
        mock_gw.return_value = mock_inverter
        mock_inverter.read_runtime_data = AsyncMock(
            return_value=BASE_RUNTIME_DATA
        )

        import inverter
        with self.assertRaises(LoopBreak):
            asyncio.run(inverter.publish(mock_client))

        # Find the wallbox/inverter publish
        wallbox_call = None
        for call in mock_client.publish.call_args_list:
            if call[0][0] == "wallbox/inverter":
                wallbox_call = call
                break
        self.assertIsNotNone(wallbox_call)

        payload = json.loads(wallbox_call[0][1])
        expected_keys = {"ppv", "load_p1", "load_p2", "load_p3",
                         "backup_i1", "backup_i2", "backup_i3",
                         "battery_soc"}
        self.assertEqual(expected_keys, set(payload.keys()))
        self.assertEqual(3000, payload["ppv"])
        self.assertEqual(85, payload["battery_soc"])


if __name__ == '__main__':
    unittest.main()
