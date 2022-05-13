"""
校验工具
"""
import re
import socket
import string
import ipaddress
from typing import Union

from _socket import gaierror

CHINA_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")

GLOBAL_PHONE_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def check_china_mobile_phone(phone: str):
    """
    中国手机号码
    """
    if not phone:
        return False
    if not phone.startswith("+86"):
        return False
    phone = phone[3:]
    match = CHINA_PHONE_RE.match(phone)
    if match and match.group() == phone:
        return True
    return False


def check_global_mobile_phone_length(phone: str):
    if not phone:
        return False
    match = GLOBAL_PHONE_RE.match(phone)
    if match and match.group() == phone:
        return True
    return False


def only_alphabetic_numeric(value: str) -> bool:
    if value is None:
        return False
    options = string.ascii_letters + string.digits + "_"
    if not all([i in options for i in value]):
        return False
    return True


def validate_ip_or_host(value: Union[int, str]):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as e:
        if isinstance(value, int):
            raise e
        try:
            socket.gethostbyname(value)
            return value
        except gaierror as e:
            raise ValueError(f"get host by {value} Failed, error: {e}")
