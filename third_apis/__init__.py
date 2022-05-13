import string
import logging
from typing import Any, Set, List, Type
from functools import partial

import requests

from common.types import RequestMethodEnum
from common.validators import validate_ip_or_host, only_alphabetic_numeric

logger = logging.getLogger(__name__)

DATA_SEND_WAYS = ["auto", "json", "params", "data"]
SCHEMAS = ["http", "https"]


class Response:
    success: bool = False
    status_code: int = None
    data: Any = None

    def __init__(self, success, status_code, data, **kwargs):
        self.success = success
        self.status_code = status_code
        self.data = data
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def parse_response(cls, raw_response: requests.Response) -> "Response":
        raise NotImplementedError

    def __repr__(self):
        return f"success: {self.success}, status_code: {self.status_code}"


class DefaultResponse(Response):
    @classmethod
    def parse_response(cls, raw_response: requests.Response) -> "Response":
        status_code = raw_response.status_code
        try:
            data = raw_response.json()
        except requests.exceptions.JSONDecodeError:
            data = raw_response.text
        return cls(success=True, status_code=status_code, data=data)


class APIBaseConfig:
    name: str
    schema: str
    host: str
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
        schema: str,
        host: str = None,
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
        if schema:
            assert schema in SCHEMAS, f"invalid request schema: {schema}"
        self.schema = schema
        if host:
            self.host = validate_ip_or_host(host)
        else:
            self.host = host
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
        schema: str = None,
        host: str = None,
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
            schema=schema,
            host=host,
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

    def __int__(
        self,
        name: str,
        schema: str,
        host: str,
        response_cls: Type[Response],
        apis: List[API] = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        cookies: dict = None,
        timeout: int = 6,
    ):
        assert all(
            [name, schema, host, response_cls]
        ), f"value required parameters: {', '.join(['name', 'schema', 'host', 'headers', 'data', 'response'])}"
        super().__init__(
            name="",
            schema=schema,
            host=host,
            headers=headers,
            params=params,
            data=data,
            json=json,
            response_cls=response_cls,
            cookies=cookies,
            timeout=timeout,
        )
        self.name = name
        if apis:
            self.apis = set(apis)
        for api in apis:
            if api.name in self._api_names:
                raise Exception(f"two API use the same name: {api.name}")
            setattr(self, api.name, partial(self.request, api=api))
            self._api_names.add(api.name)

    def register_api(self, api: API):
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
        schemas = api.schema if api.schema else self.schema
        host = api.host if api.host else self.host
        prefix = f"{schemas}://{host}"

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
            raw_response = requests.request(
                method=api.method,
                url=prefix + api.uri,
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
            return response_cls()
        else:
            logger.debug(raw_response.text)
            return self.parse_response(api, raw_response, response_cls)

    def parse_response(self, api: API, raw_response, response_cls=None):
        if not response_cls:
            response_cls = self.response_cls
            if api.response_cls:
                response_cls = api.response_cls
        _response = response_cls.parse_response(raw_response)
        _response.success = True
        return _response


if __name__ == "__main__":
    google = Third(name="Google", schema="https", host="www.google.com", response_cls=DefaultResponse, timeout=6)
    google.register_api(API("search", method="GET", uri="/search"))
    response = google.search(params={"q": "test"})
