import asyncio
import sys
import unittest
from unittest.mock import patch, MagicMock
from enum import Enum


class LoopBreak(Exception):
    pass


# Build real-looking enums so skoda.py comparisons work
class FakeChargingState(Enum):
    CHARGING = 'charging'
    NOT_READY_FOR_CHARGING = 'not ready for charging'
    READY_FOR_CHARGING = 'ready for charging'
    UNKNOWN = 'unknown charging state'


class FakeConnectionState(Enum):
    ONLINE = 'online'
    OFFLINE = 'offline'


class FakeConnectorConnectionState(Enum):
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    UNKNOWN = 'unknown unlock plug state'


# Wire the fake enums into mock modules before importing skoda
mock_charging_mod = MagicMock()
mock_charging_mod.Charging.ChargingState = FakeChargingState

mock_connector_mod = MagicMock()
mock_connector_mod.ChargingConnector.ChargingConnectorConnectionState = (
    FakeConnectorConnectionState
)

mock_vehicle_mod = MagicMock()
mock_vehicle_mod.GenericVehicle.ConnectionState = FakeConnectionState

sys.modules.setdefault('carconnectivity', MagicMock())
sys.modules['carconnectivity.carconnectivity'] = MagicMock()
sys.modules['carconnectivity.charging'] = mock_charging_mod
sys.modules['carconnectivity.charging_connector'] = mock_connector_mod
sys.modules['carconnectivity.vehicle'] = mock_vehicle_mod

import skoda  # noqa: E402


def _make_vehicle(vin, soc=80, range_km=300, charging_state=None,
                  connection_state=None, connector_state=None,
                  power=None, estimated_date=None, target_soc=None):
    """Build a mock vehicle with the given attributes."""
    if charging_state is None:
        charging_state = FakeChargingState.NOT_READY_FOR_CHARGING
    if connection_state is None:
        connection_state = FakeConnectionState.ONLINE
    if connector_state is None:
        connector_state = FakeConnectorConnectionState.DISCONNECTED

    v = MagicMock()
    v.vin.value = vin
    v.drives.drives = {"primary": MagicMock(level=MagicMock(value=soc))}
    v.drives.total_range.value = range_km
    v.charging.state.value = charging_state
    v.charging.power.value = power
    v.charging.estimated_date_reached.value = estimated_date
    v.charging.connector.connection_state.value = connector_state
    v.charging.settings.target_level.value = target_soc
    v.connection_state.value = connection_state
    return v


class TestIsPlugConnected(unittest.TestCase):
    def test_connected(self):
        v = _make_vehicle(
            "VIN1",
            connector_state=FakeConnectorConnectionState.CONNECTED,
        )
        self.assertTrue(skoda.is_plug_connected(v))

    def test_disconnected(self):
        v = _make_vehicle(
            "VIN1",
            connector_state=FakeConnectorConnectionState.DISCONNECTED,
        )
        self.assertFalse(skoda.is_plug_connected(v))

    def test_unknown(self):
        v = _make_vehicle(
            "VIN1",
            connector_state=FakeConnectorConnectionState.UNKNOWN,
        )
        self.assertFalse(skoda.is_plug_connected(v))


class TestIsCharging(unittest.TestCase):
    def test_charging_online_with_power(self):
        v = _make_vehicle(
            "VIN1",
            charging_state=FakeChargingState.CHARGING,
            connection_state=FakeConnectionState.ONLINE,
            power=7000,
        )
        self.assertTrue(skoda.is_charging(v))

    def test_not_charging_state(self):
        v = _make_vehicle(
            "VIN1",
            charging_state=FakeChargingState.NOT_READY_FOR_CHARGING,
        )
        self.assertFalse(skoda.is_charging(v))

    def test_charging_but_offline_is_stale(self):
        v = _make_vehicle(
            "VIN1",
            charging_state=FakeChargingState.CHARGING,
            connection_state=FakeConnectionState.OFFLINE,
            power=7000,
        )
        self.assertFalse(skoda.is_charging(v))

    def test_charging_but_zero_power_is_stale(self):
        v = _make_vehicle(
            "VIN1",
            charging_state=FakeChargingState.CHARGING,
            connection_state=FakeConnectionState.ONLINE,
            power=0,
        )
        self.assertFalse(skoda.is_charging(v))


class TestPublishPlugState(unittest.TestCase):
    """Verify that the main loop publishes plug_connected_* topics."""

    def _run_one_cycle(self, enyaq_connector, vw_connector):
        """Run one fetch cycle and return the mock MQTT client."""
        from config import skodaConfig
        enyaq = _make_vehicle(
            skodaConfig["vin_skoda"],
            connector_state=enyaq_connector,
        )
        vw = _make_vehicle(
            skodaConfig["vin_vw"],
            connector_state=vw_connector,
        )

        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()

        mock_cc = MagicMock()
        mock_garage = MagicMock()
        mock_garage.list_vehicles.return_value = [enyaq, vw]
        mock_cc.get_garage.return_value = mock_garage

        with patch('skoda.connect_mqtt', return_value=mock_client), \
             patch('skoda.carconnectivity.CarConnectivity',
                   return_value=mock_cc), \
             patch('skoda.asyncio.sleep', side_effect=LoopBreak):
            with self.assertRaises(LoopBreak):
                asyncio.run(skoda.main())

        return mock_client

    def _get_publish_value(self, mock_client, topic):
        for call in mock_client.publish.call_args_list:
            if call[0][0] == topic:
                return call[0][1]
        return None

    def test_publishes_plug_connected_enyaq(self):
        client = self._run_one_cycle(
            FakeConnectorConnectionState.CONNECTED,
            FakeConnectorConnectionState.DISCONNECTED,
        )
        self.assertEqual(
            self._get_publish_value(client, "home/Car/plug_connected_enyaq"),
            1,
        )
        # VW is now handled by vw_euda.py; skoda.py must ignore its VIN.
        self.assertIsNone(
            self._get_publish_value(client, "home/Car/plug_connected_vw"),
        )

    def test_publishes_plug_disconnected(self):
        client = self._run_one_cycle(
            FakeConnectorConnectionState.DISCONNECTED,
            FakeConnectorConnectionState.CONNECTED,
        )
        self.assertEqual(
            self._get_publish_value(client, "home/Car/plug_connected_enyaq"),
            0,
        )
        # VW is now handled by vw_euda.py; skoda.py must ignore its VIN.
        self.assertIsNone(
            self._get_publish_value(client, "home/Car/plug_connected_vw"),
        )


class TestPublishTargetSoc(unittest.TestCase):
    """Verify that the main loop publishes target_soc_* topics."""

    def _run_one_cycle(self, enyaq_target, vw_target):
        from config import skodaConfig
        enyaq = _make_vehicle(
            skodaConfig["vin_skoda"], target_soc=enyaq_target)
        vw = _make_vehicle(
            skodaConfig["vin_vw"], target_soc=vw_target)

        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()

        mock_cc = MagicMock()
        mock_garage = MagicMock()
        mock_garage.list_vehicles.return_value = [enyaq, vw]
        mock_cc.get_garage.return_value = mock_garage

        with patch('skoda.connect_mqtt', return_value=mock_client), \
             patch('skoda.carconnectivity.CarConnectivity',
                   return_value=mock_cc), \
             patch('skoda.asyncio.sleep', side_effect=LoopBreak):
            with self.assertRaises(LoopBreak):
                asyncio.run(skoda.main())

        return mock_client

    def _get_publish_value(self, mock_client, topic):
        for call in mock_client.publish.call_args_list:
            if call[0][0] == topic:
                return call[0][1]
        return None

    def test_publishes_target_soc(self):
        client = self._run_one_cycle(80, 90)
        self.assertEqual(
            self._get_publish_value(client, "home/Car/target_soc_enyaq"),
            80,
        )
        # VW is now handled by vw_euda.py; skoda.py must ignore its VIN.
        self.assertIsNone(
            self._get_publish_value(client, "home/Car/target_soc_vw"),
        )

    def test_skips_target_soc_when_none(self):
        client = self._run_one_cycle(None, None)
        self.assertIsNone(
            self._get_publish_value(client, "home/Car/target_soc_enyaq"),
        )
        self.assertIsNone(
            self._get_publish_value(client, "home/Car/target_soc_vw"),
        )


if __name__ == "__main__":
    unittest.main()
