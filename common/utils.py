import os
import time
import uuid
import types
import random
import string
import logging
from typing import Any, List, Union, Callable, Hashable, Optional
from asyncio import sleep
from datetime import datetime
from itertools import chain
from contextlib import contextmanager
from collections import namedtuple

import pytz
from redis import Redis
from django.http import HttpRequest
from django.db.models import QuerySet

from storages.redis import RedisUtil, get_sync_redis
from storages.redis.keys import RedisCacheKey

logger = logging.getLogger()

COMMON_TIME_STRING = "%Y-%m-%d %H:%M:%S"
COMMON_DATE_STRING = "%Y-%m-%d"


def generate_random_string(length: int, all_digits: bool = False, excludes: List = None):
    """
    生成任意长度随机字符串
    """
    if excludes is None:
        excludes = []
    if all_digits:
        all_char = string.digits
    else:
        all_char = string.ascii_letters + string.digits
    if excludes:
        for char in excludes:
            all_char.replace(char, "")
    return "".join(random.sample(all_char, length))


def get_client_ip(request: HttpRequest):
    """
    获取客户端真实ip
    :param request:
    :return:
    """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not ip:
        ip = request.META.get("REMOTE_ADDR", "")
    client_ip = ip.split(",")[-1].strip() if ip else ""
    return client_ip


# datetime util
def datetime_now():
    """
    根据 settings 配置获取当前时间
    """
    if os.environ.get("USE_TZ") == "True":
        return datetime.now(tz=pytz.utc)
    else:
        return datetime.now(pytz.timezone(os.environ.get("TIMEZONE") or "UTC"))


def commify(n: Optional[Union[int, float, str]]):
    """
    Add commas to an integer `n`.
        >>> commify(1)
        '1'
        >>> commify(123)
        '123'
        >>> commify(-123)
        '-123'
        >>> commify(1234)
        '1,234'
        >>> commify(1234567890)
        '1,234,567,890'
        >>> commify(123.0)
        '123.0'
        >>> commify(1234.5)
        '1,234.5'
        >>> commify(1234.56789)
        '1,234.56789'
        >>> commify(' %.2f ' % -1234.5)
        '-1,234.50'
        >>> commify(None)
        >>>
    """
    if n is None:
        return None

    n = str(n).strip()

    if n.startswith("-"):
        prefix = "-"
        n = n[1:].strip()
    else:
        prefix = ""

    if "." in n:
        dollars, cents = n.split(".")
    else:
        dollars, cents = n, None

    r = []
    for i, c in enumerate(str(dollars)[::-1]):
        if i and (not (i % 3)):
            r.insert(0, ",")
        r.insert(0, c)
    out = "".join(r)
    if cents:
        out += "." + cents
    return prefix + out


RedisLock = namedtuple("RedisLock", ["lock"])


def get_random_host_and_port(servers: List[str]):
    """
    host:port 列表取机取一条
    """
    if not servers:
        return "", ""
    _server = servers[random.randint(0, len(servers) - 1)]
    return _server.split(":")


def make_redis_lock(get_redis: Callable[[], Redis], timeout: int = 60):
    """
    redis key 做为锁标示，相当于资源的互斥锁，是非可重入锁注意避免死锁
    usage:
    >>> from storages.redis import keys
    >>> r_lock = make_redis_lock(get_sync_redis)
    >>> with r_lock.lock(keys.RedisCacheKey.RedisLockKey.format("name")):
    >>>    pass
    """
    redis = None

    def _get_redis() -> Redis:
        nonlocal redis

        if redis is None:
            redis = get_redis()

        return redis

    @contextmanager
    def lock(key):
        r = _get_redis()
        v = os.urandom(20)

        _acc = False

        while not _acc:
            _acc = r.set(key, v, ex=timeout, nx=True)

            if not _acc:
                sleep(1)

        try:
            yield
        finally:
            r.eval(
                """
                if redis.call("get", KEYS[1]) == ARGV[1]
                then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            """,
                [key],
                [v],
            )

    _redis_lock = RedisLock(lock=lock,)

    return _redis_lock


redis_lock = make_redis_lock(get_sync_redis)


def mapper(func, ob):
    """
    map func for list or dict
    """
    if isinstance(ob, list):
        for i in ob:
            mapper(func, i)
    elif isinstance(ob, dict):
        for k, v in ob.items():
            if isinstance(v, dict):
                mapper(func, v)
            else:
                ob[k] = func(v)
    else:
        func(ob)


def resp_serialize(v):
    """
    响应序列化函数
    """
    if isinstance(v, QuerySet):
        return list(v)

    if isinstance(v, datetime):
        return v.strftime(COMMON_TIME_STRING)

    return v


def model_to_dict(instance, fields=None, exclude=None):
    """
    model instance to dict
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        # if not getattr(f, 'editable', False):
        #     continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = f.value_from_object(instance)
    return data


def merge_dict(dict1: dict, dict2: dict = None, reverse: bool = False):
    """
    合并字典
    """
    try:
        if not dict2:
            merged = dict1
        else:
            merged = {**dict1, **dict2}
    except (AttributeError, ValueError) as e:
        raise TypeError("original and updates must be a dictionary: %s" % e)

    if not reverse:
        return merged
    else:
        return {v: k for k, v in merged.items()}


def hash_collision_reverse(_dict: dict):
    """
    反转 键值 对，冲突时使用列表解决, 只针对单层字典
    """
    ret = {}
    for k, v in _dict.items():
        if v not in ret:
            ret[v] = k
        else:
            exist = ret[v]
            if isinstance(exist, list):
                exist.append(k)
                ret[v] = exist
            else:
                ret[v] = [exist, k]
    return ret


def millseconds_to_format_str(millseconds, format_str: str = "%Y-%m-%d %H:%M:%S"):
    """时间戳装换为格式化时间"""
    return time.strftime(format_str, time.localtime(millseconds / 1000))


def format_str_to_millseconds(value):
    """格式化时间转换为时间戳"""
    value = datetime.strftime(value, "%Y-%m-%d %H:%M:%S")
    value = time.strptime(value, "%Y-%m-%d %H:%M:%S")
    return int(time.mktime(value) * 1000)


def gen_uuid():
    return str(uuid.uuid1())


def file_upload_to(instance, filename):
    name = instance.__class__.__name__
    fields = [name, gen_uuid(), filename]
    if instance.__str__():
        fields = [fields[0], instance.__str__()[:16], *fields[1:]]
    return "/".join(filter(None, fields))


def filter_dict(dict_obj: dict, callback: Callable[[Hashable, Any], dict]):
    """
    适用于字典的filter
    """
    new_dict = {}
    for (key, value) in dict_obj.items():
        if callback(key, value):
            new_dict[key] = value
    return new_dict


def flatten_list(element):
    """
    Iterable 递归展开成一级列表
    """
    flat_list = []

    def _flatten_list(e):
        if type(e) in [list, set, tuple, QuerySet]:
            for item in e:
                _flatten_list(item)
        else:
            flat_list.append(e)

    _flatten_list(element)

    return flat_list


def underscore_to_camelcase(value):
    """
    蛇形字符串 转 驼峰字符串
    """

    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(next(c)(x) if x else "_" for x in value.split("_"))  # noqa


def generate_order_no(scene_code):
    """
    生成订单号
    """
    dt = time.strftime("%Y%m%d%H%M%S", time.localtime())
    ms = int(time.time() * 1000) % 1000
    return "{}{}{}{}".format(scene_code, dt, ms, generate_random_string(6, True))


def join_params(
    params: Union[dict, list], initial=False, filter_none: bool = True, sep: str = "&", exclude_keys: List = None
):
    """
    参数拼接，用于签名请求
    """
    temp = []

    if type(params) in [dict]:
        if not initial:
            temp.append("{")
        for i, k in enumerate(sorted(params)):
            if exclude_keys and k in exclude_keys:
                continue
            v = params[k]
            if filter_none and v is None:
                continue
            if type(v) in [dict, list]:
                temp.append("{}=".format(k))
                temp.extend(join_params(v))
                if i != len(params) - 1:
                    temp.append(sep)
            else:
                temp.append("{}={}".format(k, v))
                if i != len(params) - 1:
                    temp.append(sep)
        if not initial:
            temp.append("}")
    elif type(params) in [list]:
        temp.append("[")
        for i, v in enumerate(sorted(params)):
            if filter_none and v is None:
                continue
            if type(v) in [dict, list]:
                temp.extend(join_params(v))
                if i != len(params) - 1:
                    temp.append("|")
            else:
                temp.append(str(v))
                if i != len(params) - 1:
                    temp.append("|")
        temp.append("]")

    return temp


def dynamic_model_serializer(model, parent_serializer_classes, fields):
    meta_class = types.new_class("Meta")
    setattr(meta_class, "model", model)
    setattr(meta_class, "fields", fields)
    result = types.new_class(model.__name__ + "DynamicSerializer", parent_serializer_classes, {})
    setattr(result, "Meta", meta_class)
    return result


def verify_code(phone, code, scene):
    """
    验证码校验
    """
    key = RedisCacheKey.VerifyCodeKey.format(phone=phone, scene=scene)
    stored_code = RedisUtil.get(key)
    if stored_code == code:
        RedisUtil.delete(key)
        return True
    return False


def send_verify_code(phone, code, scene, ttl=600):
    """
    发送验证码
    """
    key = RedisCacheKey.VerifyCodeKey.format(phone=phone, scene=scene)
    RedisUtil.set(key, code, ttl)
    return True
