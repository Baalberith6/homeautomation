import asyncio
import json
import os
import stat
import tempfile
import unittest

from estia_api import (
    LoginBackoff,
    ToshibaAcHttpApi,
    ToshibaAcHttpApiAuthError,
    ToshibaAcHttpApiError,
    ToshibaAcHttpApiRateLimitError,
)


class _FakeResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return self._text


class _FakeSession:
    """Stands in for aiohttp.ClientSession; no network."""

    def __init__(self, status, body):
        self._response = _FakeResponse(
            status, body if isinstance(body, str) else json.dumps(body))

    def post(self, url, **kwargs):
        return self._response

    def get(self, url, **kwargs):
        return self._response


def _login(status, body):
    api = ToshibaAcHttpApi("user", "pass")
    api.session = _FakeSession(status, body)
    return asyncio.run(api.request_api(
        api.LOGIN_PATH, post={}, headers={"Content-Type": "application/json"}))


# The reply the Toshiba cloud sent on 2026-09-29 at 09:51 and 10:23 CEST.
RATE_LIMITED = {"resObj": None, "isSuccess": False,
                "message": "Too many requests. Try again in 60 seconds.",
                "statusCode": None}


class TestErrorReplies(unittest.TestCase):
    def test_429_lowercase(self):
        with self.assertRaises(ToshibaAcHttpApiRateLimitError) as cm:
            _login(429, RATE_LIMITED)
        self.assertEqual(
            str(cm.exception),
            "HTTP 429: Too many requests. Try again in 60 seconds.")

    def test_success_lowercase(self):
        res = _login(200, {"isSuccess": True, "resObj": {"a": 1}})
        self.assertEqual(res, {"a": 1})

    def test_success_pascalcase(self):
        res = _login(200, {"IsSuccess": True, "ResObj": {"a": 1}})
        self.assertEqual(res, {"a": 1})

    def test_invalid_password(self):
        with self.assertRaises(ToshibaAcHttpApiAuthError):
            _login(200, {"IsSuccess": False,
                         "StatusCode": "InvalidUserNameorPassword",
                         "Message": "Invalid user name or password"})

    def test_non_json_body(self):
        with self.assertRaises(ToshibaAcHttpApiError) as cm:
            _login(502, "<html>Bad Gateway</html>")
        self.assertTrue(str(cm.exception).startswith("HTTP 502:"))


class TestLoginBackoff(unittest.TestCase):
    def test_steps(self):
        b = LoginBackoff()
        delays = [b.failure(t) for t in (0, 60, 360, 960, 4560)]
        self.assertEqual(delays, [60, 300, 600, 3600, 3600])

    def test_no_reset_before_an_hour(self):
        b = LoginBackoff()
        b.failure(0)
        b.success(100)
        self.assertEqual(b.failure(200), 300)

    def test_reset_after_an_hour(self):
        b = LoginBackoff()
        b.failure(0)
        b.success(3600)
        self.assertEqual(b.failure(3700), 60)


# Change 019 revision 2: the Toshiba firewall, Device-ID and the saved token.
LOGIN_OK = {"IsSuccess": True,
            "ResObj": {"access_token": "tok", "token_type": "Bearer", "consumerId": "c1"}}
DETAIL_OK = {"IsSuccess": True, "ResObj": {"ACStateData": "x"}}

# The page the gateway sent to the COP call on 2026-09-29 at 12:22:43 CEST.
FORBIDDEN_HTML = ("<html>\n<head><title>403 Forbidden</title></head>\n<body>\n"
                  "<center><h1>403 Forbidden</h1></center>\n"
                  "<hr><center>Microsoft-Azure-Application-Gateway/v2</center>\n"
                  "</body>\n</html>\n")


class _Recorder:
    """A fake aiohttp session that answers by path and records the headers of each request."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def _answer(self, url, **kwargs):
        self.calls.append((url, dict(kwargs.get("headers") or {})))
        for path, (status, body) in self.replies.items():
            if url.endswith(path):
                return _FakeResponse(status, body if isinstance(body, str) else json.dumps(body))
        raise AssertionError(f"unexpected request {url}")

    def post(self, url, **kwargs):
        return self._answer(url, **kwargs)

    def get(self, url, **kwargs):
        return self._answer(url, **kwargs)


def _client(replies, **kwargs):
    api = ToshibaAcHttpApi("user", "pass", **kwargs)
    api.session = _Recorder(replies)
    return api


class TestDeviceId(unittest.TestCase):
    def test_login_and_call_carry_device_id(self):
        api = _client({ToshibaAcHttpApi.LOGIN_PATH: (200, LOGIN_OK),
                       ToshibaAcHttpApi.AC_STATE_PATH: (200, DETAIL_OK)},
                      device_id="f358e8c78fffd63f")
        asyncio.run(api.connect())
        asyncio.run(api.get_device_detail("dev"))
        self.assertEqual([h.get("Device-ID") for _, h in api.session.calls],
                         ["f358e8c78fffd63f", "f358e8c78fffd63f"])

    def test_no_device_id_no_header(self):
        api = _client({ToshibaAcHttpApi.LOGIN_PATH: (200, LOGIN_OK),
                       ToshibaAcHttpApi.AC_STATE_PATH: (200, DETAIL_OK)})
        asyncio.run(api.connect())
        asyncio.run(api.get_device_detail("dev"))
        self.assertTrue(all("Device-ID" not in h for _, h in api.session.calls))


class TestSavedToken(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "toshiba_token_test.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _login(self):
        api = _client({ToshibaAcHttpApi.LOGIN_PATH: (200, LOGIN_OK)}, token_path=self.path)
        return api, asyncio.run(api.connect())

    def test_login_writes_file_0600(self):
        _, source = self._login()
        self.assertEqual(source, "login")
        with open(self.path) as fh:
            self.assertEqual(json.load(fh), {"access_token": "tok", "token_type": "Bearer",
                                             "consumer_id": "c1"})
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)

    def test_file_reused_without_request(self):
        self._login()
        api = _client({}, token_path=self.path)
        self.assertEqual(asyncio.run(api.connect()), "file")
        self.assertEqual(api.session.calls, [])
        self.assertEqual((api.access_token, api.access_token_type, api.consumer_id),
                         ("tok", "Bearer", "c1"))

    def test_memory_reused(self):
        api, _ = self._login()
        self.assertEqual(asyncio.run(api.connect()), "memory")
        self.assertEqual(len(api.session.calls), 1)

    def test_broken_file_logs_in(self):
        with open(self.path, "w") as fh:
            fh.write("not json")
        _, source = self._login()
        self.assertEqual(source, "login")

    def test_forget_deletes_file(self):
        api, _ = self._login()
        api.forget_token()
        self.assertFalse(os.path.exists(self.path))
        self.assertIsNone(api.access_token)


class TestStatusRules(unittest.TestCase):
    def test_403_html_is_rate_limit_one_line(self):
        with self.assertRaises(ToshibaAcHttpApiRateLimitError) as cm:
            _login(403, FORBIDDEN_HTML)
        text = str(cm.exception)
        self.assertNotIn("\n", text)
        self.assertTrue(text.startswith("HTTP 403: <html> <head><title>403 Forbidden</title>"), text)

    def test_401_forgets_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "toshiba_token_test.json")
            api = _client({ToshibaAcHttpApi.LOGIN_PATH: (200, LOGIN_OK),
                           ToshibaAcHttpApi.AC_STATE_PATH: (401, "")}, token_path=path)
            asyncio.run(api.connect())
            with self.assertRaises(ToshibaAcHttpApiAuthError):
                asyncio.run(api.get_device_detail("dev"))
            self.assertFalse(os.path.exists(path))
            self.assertIsNone(api.access_token)


class TestResetSession(unittest.TestCase):
    """Change 019 revision 3: reset_session() closes the HTTP session; the next request opens a new one."""

    def test_reset_closes_and_drops_the_session(self):
        api = ToshibaAcHttpApi("user", "pass")
        closed = []

        class _Session:
            async def close(self):
                closed.append(True)

        api.session = _Session()
        asyncio.run(api.reset_session())
        self.assertEqual(closed, [True])
        self.assertIsNone(api.session)

    def test_reset_without_session(self):
        api = ToshibaAcHttpApi("user", "pass")
        asyncio.run(api.reset_session())
        self.assertIsNone(api.session)

if __name__ == "__main__":
    unittest.main()
