import abc
import string
import logging
from typing import Any, Set, List, Type, Callable, Optional
from functools import partial

import requests

from common.types import RequestMethodEnum
from common.validators import validate_ip_or_host, only_alphabetic_numeric

logger = logging.getLogger(__name__)

DATA_SEND_WAYS = ["auto", "json", "params", "data"]
PROTOCOLS = ["http", "https"]


class Response:
    success: bool = False
    status_code: int = None
    data: Any = None
    request_context: dict

    def __init__(self, success, status_code, data, request_context, **kwargs):
        self.success = success
        self.status_code = status_code
        self.data = data
        self.request_context = request_context
        for k, v in kwargs.items():
            setattr(self, k, v)

    def json(self):
        return self.data

    @classmethod
    def parse_response(cls, raw_response: requests.Response, request_context) -> "Response":
        raise NotImplementedError

    def __repr__(self):
        return f"success: {self.success}, status_code: {self.status_code}"


class DefaultResponse(Response):
    @classmethod
    def parse_response(cls, raw_response: requests.Response, request_context) -> "Response":
        status_code = raw_response.status_code
        success = False
        try:
            data = raw_response.json()
            if data.get("code") == 0:
                success = True
        except requests.exceptions.JSONDecodeError:
            data = raw_response.text
        return cls(success=success, status_code=status_code, data=data, request_context=request_context)


class APIBaseConfig:
    name: str
    protocol: str
    host: str
    port: Optional[int]
    headers: dict
    params: dict
    data: dict
    json: dict
    response_cls: Type[Response]
    timeout: int
    cookies: dict

    def __init__(
        self,
        name: str,
        protocol: str,
        host: str = None,
        port: Optional[int] = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        response_cls: Type[Response] = None,
        cookies: dict = None,
        timeout: int = None,
    ):
        if name and isinstance(self, API):
            assert (
                only_alphabetic_numeric(name) and name[0] not in string.digits
            ), "name of api is unique identifier under third which can only contains alphabet or number or underscore"
        self.name = name
        if protocol:
            assert protocol in PROTOCOLS, f"invalid request protocol: {protocol}"
        self.protocol = protocol
        if host:
            self.host = validate_ip_or_host(host)
        else:
            self.host = host
        self.port = port
        self.headers = headers
        self.params = params
        self.data = data
        self.json = json
        self.response_cls = response_cls
        self.cookies = cookies
        self.timeout = timeout

    def __repr__(self):
        return self.name


class API(APIBaseConfig):
    method: str
    uri: str  # /xx

    def __init__(
        self,
        name: str,
        method: str,
        uri: str,
        protocol: str = None,
        host: str = None,
        port: Optional[int] = None,
        response_cls: Type[Response] = None,
        headers: dict = None,
        cookies: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        timeout: int = None,
    ):
        assert name, "name cannot be empty"
        method = method.lower()
        assert method in [m.value for m in RequestMethodEnum], f"invalid request method: {method}"
        self.method = method
        assert uri and uri.startswith("/"), "URI string must starts with '/'"
        self.uri = uri
        super().__init__(
            name=name,
            protocol=protocol,
            host=host,
            port=port,
            headers=headers,
            params=params,
            data=data,
            json=json,
            response_cls=response_cls,
            cookies=cookies,
            timeout=timeout,
        )


class Third(APIBaseConfig):
    apis: Set[API] = set()
    _api_names: Set[str] = set()
    _request = requests.request
    api_key: Optional[str] = None
    sign_key: Optional[str] = None

    def __init__(
        self,
        name: str,
        protocol: str,
        host: str,
        response_cls: Type[Response],
        port: Optional[int] = None,
        apis: List[API] = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        cookies: dict = None,
        timeout: int = 6,
        request: Optional[Callable] = None,
        api_key: Optional[str] = None,
        sign_key: Optional[str] = None,
    ):
        assert all(
            [name, protocol, host, response_cls]
        ), f"value required parameters: {', '.join(['name', 'protocol', 'host', 'headers', 'data', 'response'])}"
        super().__init__(
            name="",
            protocol=protocol,
            host=host,
            port=port,
            headers=headers,
            params=params,
            data=data,
            json=json,
            response_cls=response_cls,
            cookies=cookies,
            timeout=timeout,
        )
        self.name = name
        self.api_key = api_key
        self.sign_key = sign_key
        if apis:
            self.apis = set(apis)
            for api in apis:
                assert (
                    all([i in string.ascii_lowercase + string.ascii_uppercase + string.digits + "_" for i in api.name])
                    and api.name[0] not in string.digits
                ), "illegal api name"
                if api.name in self._api_names:
                    raise Exception(f"two API use the same name: {api.name}")
                setattr(self, api.name, partial(self.request, api=api))
                self._api_names.add(api.name)
        if request:
            self._request = request

    def register_api(self, api: API):
        assert (
            all([i in string.ascii_lowercase + string.ascii_uppercase + string.digits + "_" for i in api.name])
            and api.name[0] not in string.digits
        ), "illegal api name"
        if api.name in self._api_names:
            raise Exception(f"the {api.name} API already exists")
        self.apis.add(api)
        setattr(self, api.name, partial(self.request, api=api))

    def update_dict(self, attr_name, api, _d):
        data = getattr(self, attr_name) or {}
        api_data = getattr(api, attr_name)
        if api_data:
            data.update(api_data)
        if _d:
            data.update(_d)
        return data

    def request(
        self,
        api,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: int = None,
        **kwargs,
    ):
        protocol = api.protocol if api.protocol else self.protocol
        host = api.host if api.host else self.host
        prefix = f"{protocol}://{host}"
        port = self.port
        if api.port:
            port = api.port
        if port:
            prefix += ":" + str(port)

        request_params = self.update_dict("params", api, params)

        request_data = self.update_dict("data", api, data)

        request_json = self.update_dict("json", api, json)

        request_headers = self.update_dict("headers", api, headers)

        request_cookies = self.update_dict("cookies", api, cookies)

        if not timeout:
            timeout = self.timeout
            if api.timeout:
                timeout = api.timeout
        response_cls = kwargs.get("response_cls")
        if not response_cls:
            response_cls = self.response_cls
            if api.response_cls:
                response_cls = api.response_cls
        try:
            raw_response = self._request(
                method=api.method,
                url=prefix + api.uri,
                api_key=self.api_key,
                sign_key=self.sign_key,
                params=request_params,
                data=request_data,
                json=request_json,
                headers=request_headers,
                cookies=request_cookies,
                timeout=timeout,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"request failed: {e}")
            return response_cls(success=False, status_code=None, data=None)
        else:
            request_context = {
                    "method": api.method,
                    "url": prefix + api.uri,
                    "headers": request_headers,
                    "params": request_params,
                    "data": request_data,
                    "json": request_json,
                    "cookies": request_cookies,
                    "kwargs": kwargs,
            }
            logger.debug({"request_context": request_context})
            logger.debug({"raw_response": raw_response.text})
            return self.parse_response(
                api,
                request_context,
                raw_response,
                response_cls,
            )

    def parse_response(self, api: API, request_context: dict, raw_response, response_cls=None):
        if not response_cls:
            response_cls = self.response_cls
            if api.response_cls:
                response_cls = api.response_cls
        _response = response_cls.parse_response(raw_response, request_context)
        return _response


if __name__ == "__main__":

    class GoogleAPI(Third):
        @abc.abstractmethod
        def search(self, *args, **kwargs):
            pass

    google_apis = [API("search", method="GET", uri="/search", response_cls=DefaultResponse)]
    google_api = GoogleAPI(
        name="GoogleAPI",
        protocol="https",
        host="www.google.com",
        port=None,
        response_cls=DefaultResponse,
        timeout=6,
        request=requests.request,
        headers={"auth": ":"},
    )
    for api in google_apis:
        google_api.register_api(api)
    google_api.register_api(API("search", method="GET", uri="/search"))
    response = google_api.search(params={"q": "test"})
