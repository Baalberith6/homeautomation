import requests
import base64
import hashlib
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from common import connect_mqtt, publishProperties
from config import cezConfig, generalConfig as c
from secret import cezUsername, cezPassword

AUTH_AUTHORIZE_URL = "https://auth.cez.cz/oauth2/authorize"
TOKEN_URL = "https://api.cez.cz/token"
CLIENT_ID = "wu2tPrszYcFOKPAA2DUdDehONGAa"
REDIRECT_URI = "https://muj.cez.cz/col/"
API_BASE = "https://muj.cez.cz/col-api/prod/1.0"


def authenticate():
    """Authenticate to muj.cez.cz via OAuth2 PKCE + CAS login."""
    session = requests.Session()

    # Generate PKCE code verifier and challenge
    raw = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=")
    code_verifier = raw.decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    # Step 1: Start OAuth2 authorization (redirects to CAS login)
    r = session.get(AUTH_AUTHORIZE_URL, params={
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }, allow_redirects=True, timeout=30)

    # Step 2: Parse CAS login form
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise Exception(f"[cez] Could not find login form at {r.url}")

    execution = form.find("input", {"name": "execution"}).get("value", "")

    # Step 3: Submit credentials
    r = session.post(r.url, data={
        "username": cezUsername,
        "password": cezPassword,
        "execution": execution,
        "_eventId": "submit",
        "geolocation": "",
    }, allow_redirects=True, timeout=30)

    # Step 4: Extract authorization code from redirect URL
    params = parse_qs(urlparse(r.url).query)
    code = params.get("code", [None])[0]
    if not code:
        raise Exception(
            "[cez] No auth code in redirect: " + r.url
        )

    if c["debug"]:
        print("[cez] Got authorization code")

    # Step 5: Exchange code for access token
    token_r = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": code_verifier,
    }, timeout=30)
    token_r.raise_for_status()
    token_data = token_r.json()

    if c["debug"]:
        print(f"[cez] Token obtained, expires in {token_data['expires_in']}s")

    return token_data["access_token"]


def fetch_virtual_battery(token):
    """Fetch virtual battery data from the CEZ API."""
    r = requests.get(
        f"{API_BASE}/tapp/virtual-battery",
        params={"supplyPointUid": cezConfig["supply_point_uid"]},
        headers={
            "Authorization": f"Bearer {token}",
            "X-COL-APPID": "ODBERNE_MISTO",
            "X-COL-PARTNER": cezConfig["partner_id"],
            "X-COL-USER-CLIENT": "mc-web",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def run():
    token = authenticate()
    data = fetch_virtual_battery(token)

    if c["debug"]:
        from pprint import pprint
        pprint(data)

    charge = data["virtualBatteryActualCharge"]
    production = data["virtualBatteryAggregatedProduction"]
    consumption = data["virtualBatteryAggregatedConsumption"]
    discount = data["virtualBatteryDiscountAmount"]

    print(f"[cez] Virtual battery: {charge} kWh, "
          f"production: {production} kWh, consumption: {consumption} kWh, "
          f"discount: {discount} CZK")

    client = connect_mqtt("cez-battery")
    client.loop_start()

    client.publish("home/cez/virtual_battery", charge,
                   qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/cez/aggregated_production", production,
                   qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/cez/aggregated_consumption", consumption,
                   qos=2, properties=publishProperties).wait_for_publish()
    client.publish("home/cez/discount_amount", discount,
                   qos=2, properties=publishProperties).wait_for_publish()

    client.disconnect()
    print("[cez] Published to MQTT")


if __name__ == "__main__":
    run()
