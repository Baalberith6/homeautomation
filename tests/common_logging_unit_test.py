"""Change 020: the log format, the MQTT connect and disconnect lines, the resubscribe, and ConnectionLog.

Spec: ../kb/work/020-failures-visible-automatically/spec.md, section 2.
The new names in common.py are read inside the tests, so the old tests still run before they exist.
"""
import io
import logging
import unittest
from unittest.mock import MagicMock, patch

from paho.mqtt import client as mqtt_client
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

import common


def _stdout_of(fn):
    with patch("sys.stdout", new_callable=io.StringIO) as out:
        fn()
    return out.getvalue()


def _drop_root_stdout_handlers():
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, common.StdoutHandler):
            root.removeHandler(handler)


class TestFormat(unittest.TestCase):

    def test_setup_logging_format(self):
        log = common.get_logger("svc020")
        self.assertEqual(_stdout_of(lambda: log.error("x")), "ERROR svc020: x\n")

    def test_service_logger_info_not_debug(self):
        with patch.dict(common.c, {"debug": False}):
            log = common.get_logger("svc020info")
        self.assertEqual(_stdout_of(lambda: log.info("y")), "INFO svc020info: y\n")
        self.assertEqual(_stdout_of(lambda: log.debug("z")), "")

    def test_get_logger_twice_writes_once(self):
        common.get_logger("svc020twice")
        log = common.get_logger("svc020twice")
        self.assertEqual(_stdout_of(lambda: log.error("x")), "ERROR svc020twice: x\n")

    def test_library_warning_same_format(self):
        root_level = logging.getLogger().level
        try:
            common.setup_logging()
            lib = logging.getLogger("lib020")
            self.assertEqual(_stdout_of(lambda: lib.warning("y")), "WARNING lib020: y\n")
            self.assertEqual(_stdout_of(lambda: lib.info("i")), "")
            # A library that sets its own logger to INFO still writes no INFO line.
            chatty = logging.getLogger("lib020chatty")
            chatty.setLevel(logging.INFO)
            self.assertEqual(_stdout_of(lambda: chatty.info("i")), "")
        finally:
            _drop_root_stdout_handlers()
            logging.getLogger().setLevel(root_level)

    def test_root_stays_warning_in_debug(self):
        # netatmo.py writes the refresh token at DEBUG on its module logger; the root must never pass it.
        root_level = logging.getLogger().level
        try:
            with patch.dict(common.c, {"debug": True}):
                common.setup_logging()
            self.assertEqual(logging.getLogger().level, logging.WARNING)
        finally:
            _drop_root_stdout_handlers()
            logging.getLogger().setLevel(root_level)


class TestMqttCallbacks(unittest.TestCase):

    def setUp(self):
        self.client = common.new_client("test020")
        self.client.subscribe = MagicMock()

    def test_on_disconnect_error_with_reason(self):
        out = _stdout_of(lambda: self.client.on_disconnect(
            self.client, None, mqtt_client.MQTT_ERR_CONN_LOST, None))
        self.assertEqual(out.count("ERROR mqtt: disconnected: "), 1)
        self.assertIn(mqtt_client.error_string(mqtt_client.MQTT_ERR_CONN_LOST), out)

    def test_on_disconnect_broker_reason(self):
        reason = ReasonCode(PacketTypes.DISCONNECT, aName="Session taken over")
        out = _stdout_of(lambda: self.client.on_disconnect(self.client, None, reason, None))
        self.assertIn("ERROR mqtt: disconnected: Session taken over", out)

    def test_on_disconnect_clean_is_info(self):
        out = _stdout_of(lambda: self.client.on_disconnect(
            self.client, None, mqtt_client.MQTT_ERR_SUCCESS, None))
        self.assertEqual(out, "INFO mqtt: disconnected\n")

    def test_on_connect_subscribes_each_time(self):
        common.subscribe_on_connect(self.client, ["a/1", "b/2"])
        self.assertEqual(self.client.subscribe.call_count, 0)
        _stdout_of(lambda: self.client.on_connect(self.client, None, {}, 0, None))
        _stdout_of(lambda: self.client.on_connect(self.client, None, {}, 0, None))
        self.assertEqual([c.args[0] for c in self.client.subscribe.call_args_list],
                         ["a/1", "b/2", "a/1", "b/2"])

    def test_on_connect_logs_info(self):
        out = _stdout_of(lambda: self.client.on_connect(self.client, None, {}, 0, None))
        self.assertEqual(out, "INFO mqtt: connected\n")

    def test_subscribe_on_connect_when_connected(self):
        with patch.object(self.client, "is_connected", return_value=True):
            common.subscribe_on_connect(self.client, ["a/1"])
        self.client.subscribe.assert_called_once_with("a/1")

    def test_on_connect_failure_is_error(self):
        common.subscribe_on_connect(self.client, ["a/1"])
        reason = ReasonCode(PacketTypes.CONNACK, aName="Not authorized")
        out = _stdout_of(lambda: self.client.on_connect(self.client, None, {}, reason, None))
        self.assertIn("ERROR mqtt: connect failed: Not authorized", out)
        self.client.subscribe.assert_not_called()

    def test_connect_failure_logs_and_raises(self):
        with patch.object(common.DefaultPublishClient, "connect", side_effect=OSError("refused")):
            with patch("sys.stdout", new_callable=io.StringIO) as out:
                with self.assertRaises(OSError):
                    common.connect_mqtt("test020")
        self.assertIn("ERROR mqtt: connect to ", out.getvalue())
        self.assertIn("refused", out.getvalue())


class TestConnectionLog(unittest.TestCase):

    def setUp(self):
        self.log = common.get_logger("svc020conn")
        self.conn = common.ConnectionLog(self.log, "Thing")

    def _at(self, mono, fn):
        with patch("common.time.monotonic", return_value=mono):
            return _stdout_of(fn)

    def test_connection_log_rate_limit(self):
        out = (self._at(1000, lambda: self.conn.failed("boom"))
               + self._at(1030, lambda: self.conn.failed("boom"))
               + self._at(1061, lambda: self.conn.failed("boom")))
        self.assertEqual(out.count("ERROR svc020conn: Thing failed: boom"), 2)

    def test_connection_log_restore_once(self):
        self.assertEqual(self._at(1000, self.conn.ok), "")
        self._at(1000, lambda: self.conn.failed("boom"))
        self.assertEqual(self._at(1010, self.conn.ok), "INFO svc020conn: Thing restored\n")
        self.assertEqual(self._at(1020, self.conn.ok), "")

    def test_grace_warns_then_errors(self):
        # 020 revision 4 (owner, 2026-09-30): a short failure is a WARNING, a long one an ERROR.
        conn = common.ConnectionLog(self.log, "Portal", grace=900)
        out = (self._at(1000, lambda: conn.failed("boom"))
               + self._at(1061, lambda: conn.failed("boom")))
        self.assertNotIn("ERROR", out)
        self.assertEqual(out.count("WARNING svc020conn: Portal failed: boom"), 2)
        self.assertIn("ERROR svc020conn: Portal failed: boom", self._at(1901, lambda: conn.failed("boom")))

    def test_grace_blip_is_warning_only(self):
        conn = common.ConnectionLog(self.log, "Portal", grace=900)
        out = self._at(1000, lambda: conn.failed("boom")) + self._at(1060, conn.ok)
        self.assertNotIn("ERROR", out)
        self.assertIn("INFO svc020conn: Portal restored", out)

    def test_alert_after_three_failures(self):
        # 020 revision 9 (owner, 2026-10-01): an HTTP failure alerts on the third failure in a row.
        conn = common.ConnectionLog(self.log, "Api", alert_after=3)
        levels = [self._at(mono, lambda: conn.failed("boom")).split(" ")[0] for mono in (1000, 1060, 1120)]
        self.assertEqual(levels, ["WARNING", "WARNING", "ERROR"])

    def test_ok_resets_the_count(self):
        conn = common.ConnectionLog(self.log, "Api", alert_after=3)
        self._at(1000, lambda: conn.failed("boom"))
        self._at(1060, lambda: conn.failed("boom"))
        self._at(1070, conn.ok)
        out = self._at(1130, lambda: conn.failed("boom")) + self._at(1190, lambda: conn.failed("boom"))
        self.assertNotIn("ERROR", out)

    def test_alert_after_and_grace_both_hold(self):
        conn = common.ConnectionLog(self.log, "Api", grace=900, alert_after=3)
        out = "".join(self._at(mono, lambda: conn.failed("boom")) for mono in (1000, 1060, 1120))
        self.assertNotIn("ERROR", out)
        self.assertIn("ERROR svc020conn: Api failed: boom", self._at(1900, lambda: conn.failed("boom")))
        slow = common.ConnectionLog(self.log, "Slow", alert_after=3)
        out = self._at(1000, lambda: slow.failed("boom")) + self._at(5000, lambda: slow.failed("boom"))
        self.assertNotIn("ERROR", out)

    def test_new_failure_after_restore_logs_at_once(self):
        self._at(1000, lambda: self.conn.failed("boom"))
        self._at(1010, self.conn.ok)
        out = self._at(1020, lambda: self.conn.failed("again"))
        self.assertEqual(out, "ERROR svc020conn: Thing failed: again\n")


if __name__ == '__main__':
    unittest.main()
