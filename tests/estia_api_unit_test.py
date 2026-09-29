import asyncio
import json
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


if __name__ == "__main__":
    unittest.main()
