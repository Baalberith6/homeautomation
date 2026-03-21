import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from estia import hex_to_number, hex_to_number_2


class LoopBreak(Exception):
    pass


class TestHexToNumber(unittest.TestCase):
    def test_zero_offset(self):
        # "20" = 32, (32-32)/2 = 0
        self.assertEqual(0, hex_to_number("20"))

    def test_basic(self):
        # "80" = 128, (128-32)/2 = 48
        self.assertEqual(48, hex_to_number("80"))

    def test_min_hex(self):
        # "00" = 0, (0-32)/2 = -16
        self.assertEqual(-16, hex_to_number("00"))

    def test_max_hex(self):
        # "ff" = 255, (255-32)/2 = 111.5
        self.assertEqual(111.5, hex_to_number("ff"))


class TestHexToNumber2(unittest.TestCase):
    """Tests based on inline comment examples in estia.py (lines 19-26)."""

    def test_a4_gives_60(self):
        # "a4" = 164, (164-48)/2 + 2 = 60
        self.assertEqual(60, hex_to_number_2("a4"))

    def test_86_gives_43(self):
        # "86" = 134, (134-48)/2 = 43
        self.assertEqual(43, hex_to_number_2("86"))

    def test_74_gives_34(self):
        self.assertEqual(34, hex_to_number_2("74"))

    def test_64_gives_26(self):
        self.assertEqual(26, hex_to_number_2("64"))

    def test_60_gives_24(self):
        self.assertEqual(24, hex_to_number_2("60"))

    def test_6c_gives_30_not_29_5(self):
        # Comment says "6c -> 29.5" but formula gives 30.0
        # "6c" = 108, (108-48)/2 = 30.0 (108 < 150, no +2)
        self.assertEqual(30.0, hex_to_number_2("6c"))

    def test_boundary_below_150_no_correction(self):
        # "95" = 149, (149-48)/2 = 50.5, no +2
        self.assertEqual(50.5, hex_to_number_2("95"))

    def test_boundary_at_150_adds_correction(self):
        # "96" = 150, (150-48)/2 + 2 = 53
        self.assertEqual(53, hex_to_number_2("96"))


class TestACStateDataParsing(unittest.TestCase):
    """Verify the hex string slicing produces correct parsed data."""

    def _build_state(self, **overrides):
        """Build a 34-char ACStateData hex string with defaults."""
        # Default: water active, 48°C, no TUV, heating active,
        # manual 32°C, auto 28°C, no compressor/coil heating
        fields = {
            "water_mode": "0c",     # s[0:2]
            "water_temp": "80",     # s[2:4] -> hex_to_number = 48
            "tuv_comp": "00",       # s[4:6]
            "tuv_coil": "00",       # s[6:8]
            "heating": "03",        # s[8:10]
            "f1112": "00",          # s[10:12]
            "manual_temp": "60",    # s[12:14] -> 32
            "auto_temp": "58",      # s[14:16] -> 28
            "heat_comp": "00",      # s[16:18]
            "heat_coil": "00",      # s[18:20]
            "f2122": "00",          # s[20:22]
            "f2324": "00",          # s[22:24]
            "f2526": "00",          # s[24:26]
            "temp_min": "50",       # s[26:28] -> 24
            "f2930": "50",          # s[28:30]
            "f3132": "00",          # s[30:32]
            "f3334": "00",          # s[32:34]
        }
        fields.update(overrides)
        return "".join(fields.values())

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_parses_water_temp_and_heating_temps(self, mock_api_cls,
                                                  mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        state = self._build_state()
        mock_api.get_device_detail = AsyncMock(return_value={
            "ACStateData": state,
            "TWI_Temp": "80",
            "TWO_Temp": "70",
            "TO_Temp": "60",
        })

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        # auto_temp "58" = 28
        self.assertEqual(28, published["home/estia/target_temp"])
        # outside_temp "60": hex_to_number_2 = (96-48)/2 = 24
        self.assertEqual(24, published["home/estia/outside_temp"])

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_compressor_active_from_water(self, mock_api_cls,
                                          mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        state = self._build_state(tuv_comp="01")
        mock_api.get_device_detail = AsyncMock(return_value={
            "ACStateData": state,
            "TWI_Temp": "80",
            "TWO_Temp": "70",
            "TO_Temp": "60",
        })

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        self.assertTrue(published["bool/estia/compressor_active"])

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_compressor_active_from_heating(self, mock_api_cls,
                                             mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        state = self._build_state(heat_comp="01")
        mock_api.get_device_detail = AsyncMock(return_value={
            "ACStateData": state,
            "TWI_Temp": "80",
            "TWO_Temp": "70",
            "TO_Temp": "60",
        })

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        self.assertTrue(published["bool/estia/compressor_active"])

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_no_compressor_when_all_off(self, mock_api_cls,
                                        mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        state = self._build_state()
        mock_api.get_device_detail = AsyncMock(return_value={
            "ACStateData": state,
            "TWI_Temp": "80",
            "TWO_Temp": "70",
            "TO_Temp": "60",
        })

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        self.assertFalse(published["bool/estia/compressor_active"])


class TestTUVSuppression(unittest.TestCase):
    """When TUV (hot water) is active, in/out temps use previous values."""

    def _build_state(self, tuv_comp="00", tuv_coil="00"):
        return ("0c" + "80" + tuv_comp + tuv_coil + "03" + "00"
                + "60" + "58" + "00" + "00" + "00" + "00"
                + "00" + "50" + "50" + "00" + "00")

    @patch('estia.time.sleep', side_effect=LoopBreak)
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_tuv_off_reads_fresh_temps(self, mock_api_cls,
                                       mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api
        mock_api.get_device_detail = AsyncMock(return_value={
            "ACStateData": self._build_state(),
            "TWI_Temp": "80",  # hex_to_number_2 = (128-48)/2 = 40
            "TWO_Temp": "70",  # (112-48)/2 = 32
            "TO_Temp": "60",
        })

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        published = {
            call[0][0]: call[0][1]
            for call in mock_client.publish.call_args_list
        }
        # tuv_active_latest starts at 999, so >20 on first iteration
        self.assertEqual(40, published["home/estia/in_temp"])
        self.assertEqual(32, published["home/estia/out_temp"])

    @patch('estia.time.sleep', side_effect=[None, LoopBreak])
    @patch('estia.connect_mqtt')
    @patch('estia.ToshibaAcHttpApi')
    def test_tuv_on_uses_previous_temps(self, mock_api_cls,
                                        mock_mqtt, mock_sleep):
        mock_client = MagicMock()
        mock_client.publish.return_value = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_api = AsyncMock()
        mock_api_cls.return_value = mock_api

        # Iteration 1: TUV off → reads fresh temps (40, 32)
        # Iteration 2: TUV compressor on → uses previous (40, 32)
        mock_api.get_device_detail = AsyncMock(side_effect=[
            {
                "ACStateData": self._build_state(),
                "TWI_Temp": "80",  # 40
                "TWO_Temp": "70",  # 32
                "TO_Temp": "60",
            },
            {
                "ACStateData": self._build_state(tuv_comp="01"),
                "TWI_Temp": "90",  # would be 33 if read
                "TWO_Temp": "90",  # would be 33 if read
                "TO_Temp": "60",
            },
        ])

        import estia
        with self.assertRaises(LoopBreak):
            asyncio.run(estia.main())

        # Get the second set of publishes (iteration 2)
        in_temp_calls = [
            call for call in mock_client.publish.call_args_list
            if call[0][0] == "home/estia/in_temp"
        ]
        out_temp_calls = [
            call for call in mock_client.publish.call_args_list
            if call[0][0] == "home/estia/out_temp"
        ]
        # Iteration 2 should reuse iteration 1's values
        self.assertEqual(40, in_temp_calls[1][0][1])
        self.assertEqual(32, out_temp_calls[1][0][1])


if __name__ == '__main__':
    unittest.main()
