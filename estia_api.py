import json
import logging
import os
import typing as t
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ToshibaAcDeviceInfo:
    ac_id: str
    ac_unique_id: str
    ac_name: str
    initial_ac_state: str
    firmware_version: str
    merit_feature: str
    ac_model_id: str


@dataclass
class ToshibaAcDeviceAdditionalInfo:
    cdu: t.Optional[str]
    fcu: t.Optional[str]


class ToshibaAcHttpApiError(Exception):
    pass


class ToshibaAcHttpApiAuthError(ToshibaAcHttpApiError):
    pass


class ToshibaAcHttpApiRateLimitError(ToshibaAcHttpApiError):
    """HTTP 429 from the Toshiba cloud."""
    pass


def _pick(body: dict, *keys: str) -> t.Any:
    """The first key present in the reply; the cloud mixes PascalCase and camelCase."""
    for key in keys:
        if key in body:
            return body[key]
    return None


class LoginBackoff:
    """Wait before the next login after a failure: 60 s, 300 s, 600 s, then 3600 s.

    The step goes back to the first only after an hour with no failure, so two
    sessions that end each other cannot log in every minute (change 019).
    `now` is a monotonic time in seconds.
    """

    STEPS = (60, 300, 600, 3600)
    RESET_AFTER = 3600

    def __init__(self, steps: t.Sequence[int] = STEPS, reset_after: int = RESET_AFTER) -> None:
        self._steps = tuple(steps)
        self._reset_after = reset_after
        self._index = 0
        self._last_failure: t.Optional[float] = None

    def failure(self, now: float) -> int:
        delay = self._steps[min(self._index, len(self._steps) - 1)]
        self._index += 1
        self._last_failure = now
        return delay

    def success(self, now: float) -> None:
        if self._last_failure is None or now - self._last_failure >= self._reset_after:
            self._index = 0

    @property
    def last_step(self) -> int:
        return self._steps[-1]


class ToshibaAcHttpApi:
    BASE_URL = "https://mobileapi.toshibahomeaccontrols.com"
    LOGIN_PATH = "/api/Consumer/Login"
    REGISTER_PATH = "/api/Consumer/RegisterMobileDevice"
    AC_MAPPING_PATH = "/api/Estia/GetConsumerEstiaMapping"
    AC_STATE_PATH = "/api/Estia/GetCurrentEstiaStateByUniqueDeviceId"
    AC_ENERGY_CONSUMPTION_PATH = "/api/AC/GetGroupACEnergyConsumption"

    def __init__(self, username: str, password: str, device_id: t.Optional[str] = None,
                 token_path: t.Optional[str] = None) -> None:
        self.username = username
        self.password = password
        # Since ~2026-07-16 the cloud's firewall answers 429 to a login without a
        # Device-ID header (change 019, revision 2).
        self.device_id = device_id
        self.token_path = token_path
        self.access_token: t.Optional[str] = None
        self.access_token_type: t.Optional[str] = None
        self.consumer_id: t.Optional[str] = None
        self.session: t.Optional[aiohttp.ClientSession] = None

    def _load_token(self) -> bool:
        """Take the token from `token_path`; False when there is no usable file."""
        if not self.token_path or not os.path.exists(self.token_path):
            return False
        try:
            with open(self.token_path) as fh:
                saved = json.load(fh)
            token, token_type, consumer_id = saved["access_token"], saved["token_type"], saved["consumer_id"]
        except Exception as e:
            print(f"[estia_api] Could not load token: {e}")
            return False
        self.access_token, self.access_token_type, self.consumer_id = token, token_type, consumer_id
        return True

    def _save_token(self) -> None:
        if not self.token_path:
            return
        saved = {"access_token": self.access_token, "token_type": self.access_token_type,
                 "consumer_id": self.consumer_id}
        tmp = self.token_path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump(saved, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.token_path)

    async def reset_session(self) -> None:
        """Close the HTTP session; the next request opens a new one (change 019 revision 3).

        After an idle hour, the first call of an old session got the Azure gateway's 403 page,
        while the same token worked from a new session (2026-09-30).
        """
        if self.session:
            await self.session.close()
            self.session = None

    def forget_token(self) -> None:
        """Drop the token in memory and on disk, so the next connect() logs in."""
        self.access_token = None
        self.access_token_type = None
        self.consumer_id = None
        if self.token_path and os.path.exists(self.token_path):
            os.remove(self.token_path)

    async def request_api(
        self,
        path: str,
        get: t.Any = None,
        post: t.Any = None,
        headers: t.Any = None,
    ) -> t.Any:
        if not isinstance(headers, dict):
            if not self.access_token_type or not self.access_token:
                raise ToshibaAcHttpApiError("Failed to send request, missing access token")

            headers = {}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = self.access_token_type + " " + self.access_token
            authenticated = True
        else:
            headers = dict(headers)
            authenticated = False
        if self.device_id:
            headers["Device-ID"] = self.device_id

        url = self.BASE_URL + path

        if not self.session:
            # 30 s in total; the aiohttp default is 300 s (change 020).
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

        method_args = {"params": get, "headers": headers}

        if post:
            logger.debug(f"Sending POST to {url}")
            method_args["json"] = post
            method = self.session.post
        else:
            logger.debug(f"Sending GET to {url}")
            method = self.session.get

        async with method(url, **method_args) as response:
            status = response.status
            text = await response.text()
            logger.debug(f"Response code: {status}")

        try:
            body = json.loads(text)
        except ValueError:
            body = None

        if isinstance(body, dict):
            message = f"HTTP {status}: {_pick(body, 'Message', 'message') or ''}"
        else:
            message = f"HTTP {status}: {' '.join(text.split())[:200]}"
        # The status decides before the body: the gateway's 403 is an HTML page.
        if status in (403, 429):
            raise ToshibaAcHttpApiRateLimitError(message)
        if status == 401:
            if authenticated:
                self.forget_token()
            raise ToshibaAcHttpApiAuthError(message)
        if not isinstance(body, dict):
            raise ToshibaAcHttpApiError(message)

        if status == 200 and _pick(body, "IsSuccess", "isSuccess"):
            return _pick(body, "ResObj", "resObj")

        if _pick(body, "StatusCode", "statusCode") == "InvalidUserNameorPassword":
            raise ToshibaAcHttpApiAuthError(message)
        raise ToshibaAcHttpApiError(message)

    async def connect(self) -> str:
        """Get a session: the token in memory, else the token file, else a network login.

        Returns "memory", "file" or "login". The token lasts years, so a restart
        needs no login while the file is good (change 019, revision 2).
        """
        if self.access_token and self.access_token_type and self.consumer_id:
            return "memory"
        if self._load_token():
            return "file"

        headers = {"Content-Type": "application/json"}
        post = {"Username": self.username, "Password": self.password}

        res = await self.request_api(self.LOGIN_PATH, post=post, headers=headers)

        self.access_token = res["access_token"]
        self.access_token_type = res["token_type"]
        self.consumer_id = res["consumerId"]
        self._save_token()
        return "login"

    async def get_devices(self) -> t.List[ToshibaAcDeviceInfo]:
        if not self.consumer_id:
            raise ToshibaAcHttpApiError("Failed to send request, missing consumer id")

        get = {"consumerId": self.consumer_id}

        res = await self.request_api(self.AC_MAPPING_PATH, get=get)

        devices = []

        for group in res:
            for device in group["ACList"]:
                devices.append(
                    ToshibaAcDeviceInfo(
                        device["Id"],
                        device["DeviceUniqueId"],
                        device["Name"],
                        device["ACStateData"],
                        device["FirmwareVersion"],
                        device["MeritFeature"],
                        device["ACModelId"],
                    )
                )

        return devices

    async def get_device_detail(self, ac_unique_id: str) -> str:
        get = {
            "DeviceUniqueId": ac_unique_id,
        }

        return await self.request_api(self.AC_STATE_PATH, get=get)

    async def get_hourly_consumption(self, ac_unique_id: str, day: datetime) -> str:
        post = {
            "ACDeviceUniqueIdList": [ac_unique_id],
            "Timezone": "UTC", # seems like it doesn't matter
            "Type": "EnergyDay",
            "FromUtcTime": (day - timedelta(days=1)).strftime("%Y-%m-%d"),
            "ToUtcTime": day.strftime("%Y-%m-%d"),
            "IsEstia": True,
        }

        return await self.request_api(self.AC_ENERGY_CONSUMPTION_PATH, post=post)
