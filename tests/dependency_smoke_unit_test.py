"""Change 037: the pinned libraries still give the services what they use.

Change: ../kb/work/037-security-pins-py39/change.md, section 5.
No test opens a network connection or talks to a device.
"""
import os
import unittest

import certifi
import flask
from cryptography.fernet import Fernet
from lxml import html
from tinytuya.core import crypto_helper

TUYA_KEY = b"0123456789abcdef"
PAYLOAD = b'{"dps":{"1":true,"2":25}}'

REHAU_LIKE_PAGE = """
<html><body>
<div class="textCenter"><form><button><div>Living room</div></button></form></div>
<button class="divRooms buttonRooms">
  <input class="labelLeft pinkR fontArial roomName inputName" value="Living room"/>
  <label>21.5</label>
</button>
<span class="spanHum"><label class="labelRight greyR fontArial"> 45% </label></span>
</body></html>
"""


class DependencySmokeTest(unittest.TestCase):

    def test_fernet_round_trip(self):
        # carconnectivity encrypts its token cache with Fernet.
        f = Fernet(Fernet.generate_key())
        self.assertEqual(f.decrypt(f.encrypt(b"token")), b"token")

    def test_tinytuya_uses_pyca_cryptography(self):
        self.assertEqual(crypto_helper.CRYPTOLIB, "pyca/cryptography")

    def test_tinytuya_aes_ecb_round_trip(self):
        # Tuya protocol 3.1 to 3.4: AES-ECB with PKCS7 padding.
        cipher = crypto_helper.AESCipher(TUYA_KEY)
        enc = cipher.encrypt(PAYLOAD)
        self.assertEqual(cipher.decrypt(enc, decode_text=False), PAYLOAD)

    def test_tinytuya_aes_gcm_and_ctr_round_trip(self):
        # Tuya protocol 3.5: AES-GCM; tinytuya decrypts without the tag through CTR.
        cipher = crypto_helper.AESCipher(TUYA_KEY)
        enc = cipher.encrypt(PAYLOAD, use_base64=False, pad=False, iv=True)
        body, tag = enc[:-16], enc[-16:]
        self.assertEqual(cipher.decrypt(body, use_base64=False, decode_text=False, iv=True, tag=tag), PAYLOAD)
        self.assertEqual(cipher.decrypt(body, use_base64=False, decode_text=False, iv=True), PAYLOAD)

    def test_lxml_html_xpath(self):
        # rehau.py parses the unit's page with html.fromstring and xpath.
        tree = html.fromstring(REHAU_LIKE_PAGE)
        rooms = tree.xpath('//div[@class="textCenter"]/form/button/div/text()')
        name = tree.xpath('//button[@class="divRooms buttonRooms"]'
                          '/input[@class="labelLeft pinkR fontArial roomName inputName"]')[0].value
        temp = tree.xpath('//button[@class="divRooms buttonRooms"]/label/text()')[0]
        hum = tree.xpath('//span[@class="spanHum"]/label[@class="labelRight greyR fontArial"]/text()')[0]
        self.assertEqual(rooms, ["Living room"])
        self.assertEqual(name, "Living room")
        self.assertEqual(temp, "21.5")
        self.assertEqual(hum.strip().rstrip("%"), "45")

    def test_flask_test_client(self):
        # localweather.py serves a GET route with query arguments.
        app = flask.Flask(__name__)

        @app.route("/weather", methods=["GET"])
        def weather():
            return flask.jsonify(t=flask.request.args.get("t"))

        response = app.test_client().get("/weather?t=4.5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"t": "4.5"})

    def test_certifi_has_no_emsign(self):
        # Dependabot alert #104: emSign roots with compromised intermediates.
        self.assertTrue(os.path.exists(certifi.where()))
        with open(certifi.where(), encoding="ascii") as bundle:
            self.assertEqual(bundle.read().count("emSign"), 0)


if __name__ == "__main__":
    unittest.main()
