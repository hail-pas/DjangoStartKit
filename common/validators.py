"""
校验工具
"""
import re

PHONE_RE = re.compile(r'^1[3-9]\d{9}$')


def check_mobile_phone(phone: str):
    return PHONE_RE.match(phone.strip())
