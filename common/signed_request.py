import time
import logging

import requests

from common.utils import join_params
from common.encrypt import SignAuth

logger = logging.getLogger("common.signed_request")


def request(method, url, api_key, sign_key, **kwargs):
    timestamp = str(int(time.time()))
    headers = kwargs.get("headers", {})
    headers.update({"x-timestamp": timestamp})
    if method in ["get", "delete"]:
        sign_data = kwargs.get("params", {})
    else:
        sign_data = kwargs.get("data", {})
        sign_data.update(kwargs.get("json", {}))
    sign_data_str = "".join(join_params(sign_data, initial=True, filter_none=True))
    logger.debug(f"sign_data: {sign_data}")
    sign_data_str = f"{sign_data_str}&api_key={api_key}&timestamp={timestamp}"
    logger.debug(f"sign_data_str: {sign_data_str}")
    headers["x-sign"] = SignAuth(sign_key).generate_sign(sign_data_str)
    kwargs["headers"] = headers
    # print(f"sign_data: {sign_data}")
    # print(f"sign_data_str: {sign_data_str}")
    # print(f"api_key: {api_key}")
    # print(f"sign_key: {sign_key}")
    return requests.request(method=method, url=url, **kwargs)
