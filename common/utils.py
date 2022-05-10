import os
import sys
import random
import string
import threading
import uuid
from itertools import chain
from typing import List, Union, Optional, Callable, Any
from asyncio import sleep
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from collections import namedtuple
import pytz
from django.db.models import QuerySet
from django.http import HttpRequest
from redis import Redis
from storages.redis import get_sync_redis, keys
import time
import logging

logger = logging.getLogger()

COMMON_TIME_STRING = "%Y-%m-%d %H:%M:%S"
COMMON_DATE_STRING = "%Y-%m-%d"


def join_params(
        params: dict,
        key: str = None,
        filter_none: bool = True,
        exclude_keys: List = None,
        sep: str = "&",
        reverse: bool = False,
        key_alias: str = "key",
):
    """
    字典排序拼接参数
    """
    tmp = []
    for p in sorted(params, reverse=reverse):
        value = params[p]
        if filter_none and value in [None, ""]:
            continue
        if exclude_keys and p in exclude_keys:
            continue
        tmp.append("{0}={1}".format(p, value))
    if key:
        tmp.append("{0}={1}".format(key_alias, key))
    ret = sep.join(tmp)
    return ret


def generate_random_string(length: int, all_digits: bool = False, excludes: List = None):
    """
    生成任意长度字符串
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
        ip = request.META.get('REMOTE_ADDR', "")
    client_ip = ip.split(",")[-1].strip() if ip else ""
    return client_ip


def partial(func, *args):
    def new_func(*func_args):
        return func(*(args + func_args))

    new_func.func = func
    new_func.args = args
    return new_func


# datetime util
def datetime_now():
    if os.environ.get("USE_TZ") == "True":
        return datetime.now(tz=pytz.utc)
    else:
        return datetime.now(pytz.timezone(os.environ.get("TIMEZONE") or "UTC"))


def timelimit(timeout: Union[int, float, str]):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>>
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        RuntimeError: took too long
        >>> timelimit(1)(meaningoflife)()
        42
    _Caveat:_ The function isn't stopped after `timeout` seconds but continues
    executing in a separate thread. (There seems to be no way to kill a thread.)
    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """

    def _1(function):
        @wraps(function)
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except Exception:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.is_alive():
                raise RuntimeError("took too long")
            if c.error:
                raise c.error[1]
            return c.result

        return _2

    return _1


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
    if not servers:
        return "", ""
    thrift_server = servers[random.randint(0, len(servers) - 1)]
    return thrift_server.split(":")


def make_redis_lock(get_redis: Callable[[], Redis], timeout: int = 60):
    """
    redis key 做为锁标示，相当于资源的互斥锁，是非可重入锁注意避免死锁
    usage:
    >>> r_lock = make_redis_lock(get_sync_redis)
    >>> with r_lock.lock(keys.RedisCacheKey.redis_lock.format("name")):
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

    _redis_lock = RedisLock(lock=lock, )

    return _redis_lock


redis_lock = make_redis_lock(get_sync_redis)


def mapper(func, ob):
    """
    map func for list or dict
    :param func:
    :param ob:
    :return:
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
    if isinstance(v, QuerySet):
        return list(v)

    if isinstance(v, datetime):
        return v.strftime(COMMON_TIME_STRING)

    return v


def model_to_dict(instance, fields=None, exclude=None):
    """
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, return only the
    named.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
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
    try:
        if not dict2:
            merged = dict1
        else:
            merged = {**dict1, **dict2}
    except (AttributeError, ValueError) as e:
        raise TypeError('original and updates must be a dictionary: %s' % e)

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
    return '/'.join(filter(None, [name, instance.__str__(), gen_uuid(), filename]))


def filter_dict(dict_obj: dict, callback: Callable[[Any, Any], dict]):
    new_dict = {}
    for (key, value) in dict_obj.items():
        if callback(key, value):
            new_dict[key] = value
    return new_dict


def flatten_list(_2d_list: List):
    flat_list = []
    for element in _2d_list:
        if type(element) is list:
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list


def underscore_to_camelcase(value):
    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(next(c)(x) if x else '_' for x in value.split("_"))
