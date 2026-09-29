"""Change 020: a timeout on each HTTP call of the units, and grafana_setter skips a failed cycle.

Spec: ../kb/work/020-failures-visible-automatically/spec.md, section 2 "Timeouts".
No test opens a network connection.
"""
import asyncio
import io
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

# The committed secret.py is a stub without this name. Add it before grafana_setter is imported.
import secret
if not hasattr(secret, "grafanaApiKey"):
    secret.grafanaApiKey = ""

# rehau.py needs lxml, which the test replaces with a mock anyway.
try:
    import lxml.html  # noqa: F401
except ImportError:
    sys.modules["lxml"] = MagicMock()
    sys.modules["lxml.html"] = MagicMock()


class LoopBreak(Exception):
    """Raised by a mocked sleep to leave a while True loop."""


class TestRehauTimeouts(unittest.TestCase):

    def test_rehau_timeouts(self):
        import rehau
        with patch.object(rehau, "html", MagicMock()), \
                patch("rehau.connect_mqtt", return_value=MagicMock()), \
                patch("rehau.requests.get") as get, \
                patch("rehau.requests.post") as post, \
                patch("rehau.time.sleep", side_effect=LoopBreak), \
                patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(LoopBreak):
                asyncio.run(rehau.main())
        self.assertEqual(get.call_count, 2)
        self.assertEqual(post.call_count, 6)
        for call in get.call_args_list + post.call_args_list:
            self.assertEqual(call.kwargs.get("timeout"), 10, call)


class TestGrafanaSetter(unittest.TestCase):

    def test_grafana_setter_timeout(self):
        import grafana_setter
        with patch("grafana_setter.requests.get") as get:
            get.return_value.json.return_value = {"dashboard": {"templating": {"list": []}}}
            grafana_setter._request()
        self.assertEqual(get.call_args.kwargs.get("timeout"), 4)

    def _one_cycle(self, side_effect=None, json_value=None, json_error=None):
        import common
        import grafana_setter
        client = MagicMock()
        fresh = common.ConnectionLog(grafana_setter.log, "Grafana API")
        with patch.object(grafana_setter, "api_log", fresh), \
                patch("grafana_setter.requests.get") as get, \
                patch("grafana_setter.time.sleep", side_effect=LoopBreak), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            if side_effect is not None:
                get.side_effect = side_effect
            elif json_error is not None:
                get.return_value.json.side_effect = json_error
            else:
                get.return_value.json.return_value = json_value
            with self.assertRaises(LoopBreak):
                asyncio.run(grafana_setter.publish(client))
        return client, out.getvalue()

    def test_skips_cycle_on_timeout(self):
        client, out = self._one_cycle(side_effect=requests.Timeout("read timed out"))
        client.publish.assert_not_called()
        self.assertEqual(out.count("ERROR grafana_setter:"), 1)

    def test_skips_cycle_on_bad_json(self):
        client, out = self._one_cycle(json_error=json.JSONDecodeError("Expecting value", "", 0))
        client.publish.assert_not_called()
        self.assertEqual(out.count("ERROR grafana_setter:"), 1)

    def test_skips_cycle_on_missing_key(self):
        client, out = self._one_cycle(json_value={"message": "Unauthorized"})
        client.publish.assert_not_called()
        self.assertEqual(out.count("ERROR grafana_setter:"), 1)

    def test_publishes_on_success(self):
        variables = {"dashboard": {"templating": {"list": [
            {"name": "WallboxMode", "current": {"value": "Auto"}}]}}}
        client, out = self._one_cycle(json_value=variables)
        client.publish.assert_called_once_with("command/WallboxMode", "Auto")
        self.assertNotIn("ERROR", out)


class _Response:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return json.dumps({"IsSuccess": True, "ResObj": {"ok": 1}})


class _Session:
    def post(self, url, **kwargs):
        return _Response()

    def get(self, url, **kwargs):
        return _Response()


class TestEstiaApiTimeout(unittest.TestCase):

    def test_estia_api_session_timeout(self):
        import estia_api
        with patch.object(estia_api.aiohttp, "ClientSession", return_value=_Session()) as session:
            api = estia_api.ToshibaAcHttpApi("user", "pass")
            asyncio.run(api.request_api(api.LOGIN_PATH, post={},
                                        headers={"Content-Type": "application/json"}))
        timeout = session.call_args.kwargs.get("timeout")
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout.total, 30)


if __name__ == '__main__':
    unittest.main()
