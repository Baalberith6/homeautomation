"""The VW EU Data Act portal moved hosts (change 040).

On 2026-11-16 VW moved the portal from eu-data-act.drivesomethinggreater.com
to eu-data-act.vwgroup-datahub.com. The old host 301s its API paths to a path
that 404s. The OAuth client keeps its redirect URI on the old host, which
301s /login to the new host. These tests need no network and no credentials.
"""
import os
import sys
import unittest
from urllib.parse import parse_qs, urlparse

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vw_euda_auth as auth  # noqa: E402

NEW = "https://eu-data-act.vwgroup-datahub.com"
LEGACY = "https://eu-data-act.drivesomethinggreater.com"

# One VW identity form step: the fields the login parser needs.
_FORM = ('<form action="/signin-service/v1/x/login/step">'
         '<input name="_csrf" value="c"><input name="hmac" value="h">'
         '</form>')


class _Resp:
    def __init__(self, url, text="", status_code=200):
        self.url = url
        self.text = text
        self.status_code = status_code


class _FakeSession:
    """Replays the login: authorize page, password page, portal landing."""

    def __init__(self, landing, token=True):
        self.cookies = requests.cookies.RequestsCookieJar()
        self._landing = landing
        self._token = token
        self._posts = 0

    def get(self, url, **kwargs):
        if url.startswith(auth.cfg["identity_base"]):
            return _Resp("https://identity.vwgroup.io/signin-service/v1/x",
                         _FORM)
        return _Resp(url, "", 406)   # the portal root: ignored by login()

    def post(self, url, **kwargs):
        self._posts += 1
        if self._posts == 1:
            return _Resp("https://identity.vwgroup.io/signin-service/v1/x/"
                         "login/authenticate", _FORM)
        if self._token:
            self.cookies.set("access_token", "jwt")
        return _Resp(self._landing, "", 404)


def _client(session):
    """An EudaClient with a fake session and no credentials from secret.py."""
    c = object.__new__(auth.EudaClient)
    c._email, c._password = "user@example.com", "pw"
    c._session = session
    c._logged_in = False
    c._cookie_file = None
    return c


class TestPortalUrls(unittest.TestCase):

    def test_api_urls_use_new_host(self):
        for url in (auth._METADATA, auth._LIST, auth._DOWNLOAD):
            self.assertTrue(url.startswith(NEW + "/proxy_api/euda-apim/"), url)

    def test_relation_url_uses_new_host(self):
        c = _client(_FakeSession(NEW + "/"))
        seen = []
        c.get_json = lambda url, headers=None: seen.append(url) or {}
        c.relation_nickname("VIN")
        self.assertEqual(
            seen, [NEW + "/proxy_api/vum/v2/users/me/relations/VIN"])

    def test_redirect_uri_on_legacy_host(self):
        url = auth.EudaClient._build_authorize_url()
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["redirect_uri"], [LEGACY + "/login"])


class TestLoginLanding(unittest.TestCase):

    def test_landing_on_new_host_ok(self):
        c = _client(_FakeSession(NEW + "/cz/en/home"))
        c.login()
        self.assertTrue(c._logged_in)

    def test_landing_on_legacy_host_ok(self):
        c = _client(_FakeSession(LEGACY + "/cz/en/home"))
        c.login()
        self.assertTrue(c._logged_in)

    def test_landing_on_other_host_fails(self):
        c = _client(_FakeSession("https://example.com/cz/en/home"))
        with self.assertRaises(auth.AuthError):
            c.login()
        self.assertFalse(c._logged_in)

    def test_landing_without_token_fails(self):
        c = _client(_FakeSession(NEW + "/cz/en/home", token=False))
        with self.assertRaises(auth.AuthError):
            c.login()


class _RecordingSession(_FakeSession):
    """A fake session that records the cookie names of each GET."""

    def __init__(self, landing, token=True):
        super().__init__(landing, token)
        self.sent = []

    def get(self, url, **kwargs):
        self.sent.append(sorted(ck.name for ck in self.cookies))
        return super().get(url, **kwargs)


def _stale(session):
    """Fill the jar as the pickle of 2026-11-16 did (change 041)."""
    session.cookies.set("SESSION", "old", domain="identity.vwgroup.io")
    session.cookies.set("JSESSIONID", "old", domain="identity.vwgroup.io")
    session.cookies.set("access_token", "old",
                        domain="eu-data-act.drivesomethinggreater.com")
    return session


class TestStaleJar(unittest.TestCase):
    """The login starts with an empty cookie jar (change 041)."""

    def test_no_old_cookie_sent(self):
        s = _stale(_RecordingSession(NEW + "/cz/en/home"))
        _client(s).login()
        # The priming GET and the authorize GET carry no cookie.
        self.assertEqual(s.sent, [[], []])

    def test_old_token_does_not_pass_login(self):
        s = _stale(_FakeSession(NEW + "/cz/en/home", token=False))
        c = _client(s)
        with self.assertRaises(auth.AuthError):
            c.login()
        self.assertFalse(c._logged_in)

    def test_stale_jar_login_ok(self):
        s = _stale(_FakeSession(NEW + "/cz/en/home"))
        c = _client(s)
        c.login()
        self.assertTrue(c._logged_in)
        self.assertEqual([(ck.name, ck.value) for ck in s.cookies],
                         [("access_token", "jwt")])


if __name__ == "__main__":
    unittest.main()
