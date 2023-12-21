import logging
import typing as t
from dataclasses import dataclass

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


class ToshibaAcHttpApi:
    BASE_URL = "https://mobileapi.toshibahomeaccontrols.com"
    LOGIN_PATH = "/api/Consumer/Login"
    REGISTER_PATH = "/api/Consumer/RegisterMobileDevice"
    AC_MAPPING_PATH = "/api/Estia/GetConsumerEstiaMapping"
    AC_STATE_PATH = "/api/Estia/GetCurrentEstiaStateByUniqueDeviceId"
    AC_ENERGY_CONSUMPTION_PATH = "/api/Estia/GetGroupEstiaEnergyConsumption"

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.access_token: t.Optional[str] = None
        self.access_token_type: t.Optional[str] = None
        self.consumer_id: t.Optional[str] = None
        self.session: t.Optional[aiohttp.ClientSession] = None

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

        url = self.BASE_URL + path

        if not self.session:
            self.session = aiohttp.ClientSession()

        method_args = {"params": get, "headers": headers}

        if post:
            logger.debug(f"Sending POST to {url}")
            method_args["json"] = post
            method = self.session.post
        else:
            logger.debug(f"Sending GET to {url}")
            method = self.session.get

        async with method(url, **method_args) as response:
            json = await response.json()
            logger.debug(f"Response code: {response.status}")

            err_type = ToshibaAcHttpApiError

            if response.status == 200:
                if json["IsSuccess"]:
                    return json["ResObj"]
                else:
                    if json["StatusCode"] == "InvalidUserNameorPassword":
                        err_type = ToshibaAcHttpApiAuthError

            raise err_type(json["Message"])

    async def connect(self) -> None:
        headers = {"Content-Type": "application/json"}
        post = {"Username": self.username, "Password": self.password}

        res = await self.request_api(self.LOGIN_PATH, post=post, headers=headers)

        self.access_token = res["access_token"]
        self.access_token_type = res["token_type"]
        self.consumer_id = res["consumerId"]

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
