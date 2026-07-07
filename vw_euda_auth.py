"""Authenticated client for the VW EU Data Act portal.

VW shut down the online API the carconnectivity library used, so the ID.3 is
now read from the EU-Data-Act-mandated self-service portal
(eu-data-act.drivesomethinggreater.com), which emits a ~15-min ZIP export of a
flat key/value telemetry dump.

Auth is the VW ID (identity.vwgroup.io) OIDC form-login, pointed at the
portal's OAuth client. The login redirect chain drops an `access_token` (a
60-min VW ID JWT) plus session cookies into the cookie jar; subsequent
proxy_api calls just carry the jar.

The fragile OIDC form-scraping flow is ported from the MIT-licensed
mikrohard/hass-vw-eu-data-act (via jochen/vw-euda-mqtt), adapted to
synchronous `requests` and this project's config/secret layout.
"""
import io
import json
import os
import pickle
import re
import uuid
import zipfile
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlparse

import requests

from config import generalConfig as c
from config import vwEudaConfig as cfg
from secret import carConnectivityConfig

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
NO_CONTENT_SUFFIX = "_no_content_found.zip"

_AUTHORIZE_URL = cfg["identity_base"] + "/oidc/v1/authorize"
_REDIRECT_URI = cfg["base_url"] + "/login"
_STATE = f"{cfg['country']}__{cfg['language']}__{cfg['brand']}"
_METADATA = (cfg["base_url"] +
             "/proxy_api/euda-apim/datarequest/vehicles/{vin}/metadata/partial")
_LIST = (cfg["base_url"] +
         "/proxy_api/euda-apim/datadelivery/vehicles/{vin}/{ident}/list")
_DOWNLOAD = (cfg["base_url"] +
             "/proxy_api/euda-apim/datadelivery/vehicles/{vin}/{ident}/download")


class ApiError(Exception):
    """Generic portal API failure."""


class AuthError(ApiError):
    """Authentication failed or session expired."""


def _credentials():
    """Return (email, password) from the shared carconnectivity config."""
    connectors = carConnectivityConfig["carConnectivity"]["connectors"]
    for conn in connectors:
        conf = conn.get("config", {})
        if conf.get("username") and conf.get("password"):
            return conf["username"], conf["password"]
    raise AuthError("No username/password found in carConnectivityConfig")


class _FormParser(HTMLParser):
    """Extract the first <form> action and all input fields."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}
        self._in_form = False
        self._done = False

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        a = dict(attrs)
        if tag == "form" and self.action is None:
            self.action = a.get("action")
            self._in_form = True
        elif tag == "input" and self._in_form:
            name = a.get("name")
            if name:
                self.fields[name] = a.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "form" and self._in_form:
            self._in_form = False
            self._done = True


def _template_model(html):
    """Extract the VW identity `templateModel` JSON embedded in the page.

    The signin/authenticate pages carry form state (hmac, relayState, error)
    in a `window._IDK = { templateModel: {...} }` JS object, not HTML inputs.
    """
    idx = html.find("templateModel")
    if idx == -1:
        return {}
    brace = html.find("{", idx)
    if brace == -1:
        return {}
    depth = 0
    for i in range(brace, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[brace:i + 1])
                except ValueError:
                    return {}
    return {}


def _csrf(html):
    m = re.search(r"csrf_token\s*[:=]\s*['\"]([^'\"]+)['\"]", html)
    return m.group(1) if m else None


def _login_fields(html):
    """Collect fields for a VW identity login step (HTML inputs + JS model)."""
    parser = _FormParser()
    parser.feed(html)
    fields = dict(parser.fields)
    model = _template_model(html)
    for key in ("hmac", "relayState"):
        if model.get(key):
            fields[key] = model[key]
    email = (model.get("emailPasswordForm") or {}).get("email")
    if email:
        fields.setdefault("email", email)
    csrf = _csrf(html)
    if csrf:
        fields.setdefault("_csrf", csrf)
    return fields, parser.action


def _login_error(html):
    model = _template_model(html)
    err = model.get("error") or model.get("errorCode")
    if isinstance(err, dict):
        return err.get("text") or err.get("errorCode") or str(err)
    return str(err) if err else None


class EudaClient:
    """Authenticated, session-reusing client for the EU Data Act portal."""

    def __init__(self):
        self._email, self._password = _credentials()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._logged_in = False
        self._cookie_file = cfg.get("cookie_file")
        self._load_cookies()

    # -- cookie persistence (lockout safety: reuse a session across polls) --

    def _load_cookies(self):
        if not self._cookie_file or not os.path.exists(self._cookie_file):
            return
        try:
            with open(self._cookie_file, "rb") as fh:
                self._session.cookies.update(pickle.load(fh))
            # Assume a persisted jar is usable; a 401 triggers re-login.
            self._logged_in = True
            if c["debug"]:
                print("[vw_euda] Loaded cookies from disk")
        except Exception as e:
            print(f"[vw_euda] Could not load cookies: {e}")

    def _save_cookies(self):
        if not self._cookie_file:
            return
        try:
            with open(self._cookie_file, "wb") as fh:
                pickle.dump(self._session.cookies, fh)
        except Exception as e:
            print(f"[vw_euda] Could not save cookies: {e}")

    # -- authentication ----------------------------------------------------

    @staticmethod
    def _build_authorize_url():
        params = {
            "client_id": cfg["client_id"],
            "response_type": "code",
            "scope": cfg["scope"],
            "state": _STATE,
            "redirect_uri": _REDIRECT_URI,
            "prompt": "login",
        }
        return f"{_AUTHORIZE_URL}?{urlencode(params)}"

    def login(self):
        """Run the full OIDC login, populating the session cookie jar."""
        s = self._session
        portal_host = urlparse(cfg["base_url"]).netloc

        # 0. Prime the portal session (sets AEM/load-balancer cookies).
        try:
            s.get(cfg["base_url"] + "/", timeout=20)
        except requests.RequestException as e:
            if c["debug"]:
                print(f"[vw_euda] priming GET failed (ignored): {e}")

        # 1. Start OIDC at the identity provider (authorize URL built
        #    directly; the portal's redirect servlet 500s for non-browsers).
        r = s.get(self._build_authorize_url(), timeout=20)
        signin_url, signin_html = r.url, r.text

        # 2. POST the email (identifier step).
        fields, action = _login_fields(signin_html)
        if "hmac" not in fields or "_csrf" not in fields:
            raise AuthError(
                f"Could not parse sign-in form (fields: {sorted(fields)})")
        fields["email"] = self._email
        r = s.post(urljoin(signin_url, action or ""), data=fields,
                   headers={"Referer": signin_url}, timeout=20)
        auth_url, auth_html = r.url, r.text

        # 3. Password (authenticate) page: fields live in the JS model.
        fields2, action2 = _login_fields(auth_html)
        if "hmac" not in fields2 or "_csrf" not in fields2:
            raise AuthError(
                _login_error(auth_html)
                or "Identity portal did not return the password form "
                "(check the email address or the login flow changed)")
        fields2["email"] = self._email
        fields2["password"] = self._password
        # Post to the clean authenticate action; keeping ?relayState= 400s.
        if action2:
            authenticate_action = urljoin(auth_url, action2)
        else:
            authenticate_action = auth_url.split("?", 1)[0]

        # 4. POST credentials; follow redirects back to the portal, which
        #    sets the session cookies via /services/callbacklogin.
        r = s.post(authenticate_action, data=fields2,
                   headers={"Referer": auth_url}, timeout=20)
        landing = r.url
        if r.status_code >= 400:
            raise AuthError(
                _login_error(r.text) or f"Login rejected (HTTP {r.status_code})")
        if "signin-service" in landing or "/error" in landing:
            raise AuthError("Login failed - check email and password")
        if urlparse(landing).netloc != portal_host:
            raise AuthError(f"Login did not complete (ended at {landing})")

        self._logged_in = True
        self._save_cookies()
        if c["debug"]:
            print("[vw_euda] Login OK, access_token present:",
                  "access_token" in [ck.name for ck in s.cookies])

    def ensure_login(self):
        if not self._logged_in:
            self.login()

    # -- authenticated requests -------------------------------------------

    def _get(self, url, headers=None, _retry=True):
        self.ensure_login()
        try:
            r = self._session.get(url, headers=headers or {}, timeout=30)
        except requests.RequestException as e:
            raise ApiError(f"Connection error for {url}: {e}") from e
        if r.status_code in (401, 403) and _retry:
            if c["debug"]:
                print(f"[vw_euda] Session expired ({r.status_code}); "
                      "re-authenticating")
            self._logged_in = False
            self.login()
            return self._get(url, headers=headers, _retry=False)
        if r.status_code >= 400:
            raise ApiError(f"GET {url} -> HTTP {r.status_code}")
        return r

    def get_json(self, url, headers=None):
        r = self._get(url, headers=headers)
        try:
            return r.json()
        except ValueError as e:
            raise ApiError(f"Invalid JSON from {url}: {e}") from e

    def get_identifier(self, vin):
        """Return the standing data-request Identifier for a VIN."""
        meta = self.get_json(_METADATA.format(vin=vin),
                             headers={"type": "partial"})
        ident = meta.get("Identifier")
        if not ident:
            raise ApiError(f"No Identifier in metadata: {meta}")
        return ident

    def list_datasets(self, vin, ident):
        """Return [{name, createdOn, size}], newest-first (portal order)."""
        url = _LIST.format(vin=vin, ident=ident)
        data = self.get_json(url, headers={"type": "partial"})
        files = data if isinstance(data, list) else data.get("files", [])
        return [f for f in files
                if not str(f.get("name", "")).endswith(NO_CONTENT_SUFFIX)]

    def download_dataset(self, vin, ident, name):
        """Download one ZIP by name and return the parsed JSON inside it."""
        url = _DOWNLOAD.format(vin=vin, ident=ident)
        headers = {"filename": name, "type": "partial"}
        r = self._get(url, headers=headers)
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                members = [n for n in zf.namelist()
                           if n.lower().endswith(".json")]
                if not members:
                    raise ApiError(f"No JSON inside {name}")
                return json.loads(zf.read(members[0]).decode("utf-8"))
        except (zipfile.BadZipFile, ValueError) as e:
            raise ApiError(f"Could not read {name}: {e}") from e

    def relation_nickname(self, vin):
        """Best-effort friendly vehicle name (e.g. 'ID.3'). None on failure."""
        url = (cfg["base_url"] +
               f"/proxy_api/vum/v2/users/me/relations/{vin}")
        try:
            rel = self.get_json(
                url, headers={"traceid": f"vehicle-relation-{uuid.uuid4()}"})
            return (rel.get("relation") or {}).get("vehicleNickname")
        except ApiError:
            return None
