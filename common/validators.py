"""
校验工具
"""
import re

CHINA_PHONE_RE = re.compile(r'^1[3-9]\d{9}$')

GLOBAL_PHONE_RE = re.compile(r'^\+[1-9]\d{1,14}$')


def check_china_mobile_phone(phone: str):
    """
    中国手机号码
    """
    if phone.startswith("+86"):
        phone = phone[3:]
    return CHINA_PHONE_RE.match(phone.strip())


def check_global_mobile_phone_length(phone: str):
    return GLOBAL_PHONE_RE.match(phone.strip())
