import asyncio
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import car
from config import skodaConfig


class LoopBreak(Exception):
    pass


class TestCalculateChargingTimeRemaining(unittest.TestCase):
    """Tests for calculate_charging_time_remaining (same in car.py/skoda.py)."""

    @patch('car.datetime')
    def test_charging_60_min_remaining(self, mock_dt):
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        vehicle = MagicMock()
        vehicle.charging.power.value = 7000
        completion = datetime(2024, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        vehicle.charging.estimated_date_reached.value = completion

        self.assertEqual(60, car.calculate_charging_time_remaining(vehicle))

    @patch('car.datetime')
    def test_charging_90_min_remaining(self, mock_dt):
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        vehicle = MagicMock()
        vehicle.charging.power.value = 11000
        completion = datetime(2024, 6, 15, 13, 30, 0, tzinfo=timezone.utc)
        vehicle.charging.estimated_date_reached.value = completion

        self.assertEqual(90, car.calculate_charging_time_remaining(vehicle))

    def test_not_charging_returns_none(self):
        vehicle = MagicMock()
        vehicle.charging.power.value = 0

        self.assertIsNone(car.calculate_charging_time_remaining(vehicle))

    @patch('car.datetime')
    def test_no_estimated_completion_returns_none(self, mock_dt):
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        vehicle = MagicMock()
        vehicle.charging.power.value = 7000
        vehicle.charging.estimated_date_reached.value = None

        self.assertIsNone(car.calculate_charging_time_remaining(vehicle))

    @patch('car.datetime')
    def test_completion_in_past_returns_zero(self, mock_dt):
        now = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        vehicle = MagicMock()
        vehicle.charging.power.value = 7000
        # Completion was 30 min ago
        completion = datetime(2024, 6, 15, 13, 30, 0, tzinfo=timezone.utc)
        vehicle.charging.estimated_date_reached.value = completion

        self.assertEqual(0, car.calculate_charging_time_remaining(vehicle))

    @patch('car.datetime')
    def test_fractional_minutes_truncated(self, mock_dt):
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        vehicle = MagicMock()
        vehicle.charging.power.value = 7000
        # 45 min 30 sec → should return 45 (int truncation)
        completion = datetime(2024, 6, 15, 12, 45, 30, tzinfo=timezone.utc)
        vehicle.charging.estimated_date_reached.value = completion

        self.assertEqual(45, car.calculate_charging_time_remaining(vehicle))


class TestVINRouting(unittest.TestCase):
    """Verify vehicles publish to correct MQTT topics based on VIN."""

    def _make_vehicle(self, vin, soc=80, range_km=250, power=0):
        v = MagicMock()
        v.vin.value = vin
        v.drives.drives = {"primary": MagicMock()}
        v.drives.drives["primary"].level.value = soc
        v.drives.total_range.value = range_km
        v.charging.power.value = power
        return v

    @patch('car.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('car.carconnectivity.CarConnectivity')
    @patch('car.connect_mqtt')
    def test_enyaq_publishes_to_enyaq_topics(self, mock_mqtt, mock_cc_cls,
                                              mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        garage = MagicMock()
        mock_cc.get_garage.return_value = garage

        enyaq = self._make_vehicle(skodaConfig["vin_skoda"], soc=75,
                                   range_km=300)
        garage.list_vehicles.return_value = [enyaq]

        with self.assertRaises(LoopBreak):
            asyncio.run(car.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        self.assertEqual(75, published["home/Car/battery_level_enyaq"])
        self.assertEqual(300, published["home/Car/electric_range_enyaq"])
        self.assertNotIn("home/Car/battery_level_vw", published)

    @patch('car.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('car.carconnectivity.CarConnectivity')
    @patch('car.connect_mqtt')
    def test_vw_publishes_to_vw_topics(self, mock_mqtt, mock_cc_cls,
                                        mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        garage = MagicMock()
        mock_cc.get_garage.return_value = garage

        vw = self._make_vehicle(skodaConfig["vin_vw"], soc=60,
                                range_km=180)
        garage.list_vehicles.return_value = [vw]

        with self.assertRaises(LoopBreak):
            asyncio.run(car.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        self.assertEqual(60, published["home/Car/battery_level_vw"])
        self.assertEqual(180, published["home/Car/electric_range_vw"])
        self.assertNotIn("home/Car/battery_level_enyaq", published)

    @patch('car.asyncio.sleep', new_callable=AsyncMock,
           side_effect=LoopBreak)
    @patch('car.carconnectivity.CarConnectivity')
    @patch('car.connect_mqtt')
    def test_charging_time_published_only_when_charging(self, mock_mqtt,
                                                         mock_cc_cls,
                                                         mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc
        garage = MagicMock()
        mock_cc.get_garage.return_value = garage

        # Not charging (power=0)
        enyaq = self._make_vehicle(skodaConfig["vin_skoda"], power=0)
        garage.list_vehicles.return_value = [enyaq]

        with self.assertRaises(LoopBreak):
            asyncio.run(car.main())

        topics = [call[0][0] for call in mock_client.publish.call_args_list]
        self.assertNotIn("home/Car/charging_time_left", topics)


if __name__ == '__main__':
    unittest.main()
