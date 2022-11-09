import sys
import enum
import inspect
import threading
from typing import List, Union
from functools import wraps
from functools import partial as raw_partial

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, serializers
from django.forms.utils import pretty_name
from rest_framework.decorators import MethodMapper
from rest_framework.exceptions import PermissionDenied

from common.types import PlainSchema
from common.utils import underscore_to_camelcase


def partial(func, *args):
    """
    保留函数签名的partial装饰器
    """

    def new_func(*func_args):
        return func(*(args + func_args))

    new_func.func = func
    new_func.args = args
    return new_func


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


class ClassPropertyDescriptor(object):
    def __init__(self, fget, fset=None):  # noqa
        self.fget = fget  # noqa
        self.fset = fset  # noqa

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func  # noqa
        return self


def classproperty(func):
    """
    类属性
    """
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


def custom_swagger_auto_schema(**kwargs):
    """
    通过 query_serializer、request_body 校验 param、data、json 传参, validated_data 存入 request.param_data、 request.body_data
    """
    from core.restful import HideInspector, NoPagingAutoSchema
    from apis.responses import _Resp  # noqa

    def decorator(func):
        responses = kwargs.get("responses")
        if responses:
            responses_200_ser = responses.get(str(status.HTTP_200_OK)) or responses.get(status.HTTP_200_OK)  # noqa
            if (
                responses_200_ser
                and not isinstance(responses_200_ser, openapi.Schema)
                and not isinstance(responses_200_ser, openapi.Response)
            ):
                page_info = kwargs.get("page_info", False)

                _is_serializer_class = inspect.isclass(responses_200_ser) and (
                    issubclass(responses_200_ser, serializers.Serializer or issubclass(responses_200_ser, PlainSchema))
                )
                _is_serializer_instance = isinstance(responses_200_ser, serializers.Serializer)
                _is_list_serializer_instance = isinstance(responses_200_ser, serializers.ListSerializer)

                assert (
                    _is_serializer_class or _is_serializer_instance or _is_list_serializer_instance  # noqa
                ), f"Serializer class or instance or openapi.Schema required, not {type(responses_200_ser)}"

                if _is_serializer_class:
                    if page_info:
                        responses_200_ser = responses_200_ser(many=True)
                    else:
                        responses_200_ser = responses_200_ser()
                if _is_serializer_instance and page_info:
                    raise RuntimeError("Single Response Item Cannot with PageInfo")
                kwargs["responses"][str(status.HTTP_200_OK)] = _Resp.to_serializer(  # noqa
                    resp_serializer=responses_200_ser, page_info=page_info
                )
        view_method = raw_partial(  # swagger文档中get请求去除多余默认参数
            swagger_auto_schema, auto_schema=NoPagingAutoSchema, filter_inspectors=[HideInspector],
        )(**kwargs)(func)
        view_method.query_serializer = kwargs.get("query_serializer", None)
        view_method.body_serializer = kwargs.get("request_body", None)
        return view_method

    return decorator


def camelCaseAction(methods=None, detail=None, url_path=None, url_name=None, **kwargs):
    """
    生成驼峰路径的action
    """
    methods = ["get"] if (methods is None) else methods
    methods = [method.lower() for method in methods]

    assert detail is not None, "@action() missing required argument: 'detail'"

    # name and suffix are mutually exclusive
    if "name" in kwargs and "suffix" in kwargs:
        raise TypeError("`name` and `suffix` are mutually exclusive arguments.")

    def decorator(func):
        func.mapping = MethodMapper(func, methods)

        func.detail = detail
        func.url_path = url_path if url_path else underscore_to_camelcase(func.__name__)
        func.url_name = url_name if url_name else func.__name__.replace("_", "-")

        # These kwargs will end up being passed to `ViewSet.as_view()` within
        # the router, which eventually delegates to Django's CBV `View`,
        # which assigns them as instance attributes for each request.
        func.kwargs = kwargs

        if "name" not in kwargs and "suffix" not in kwargs:
            func.kwargs["name"] = pretty_name(func.__name__)
        func.kwargs["description"] = func.__doc__ or None

        return func

    return decorator


def extend_enum(*inherited_enums):
    def wrapper(added_enum):
        joined = {}
        for inherited_enum in inherited_enums:
            for item in inherited_enum:
                joined[item.name] = item.value
            for item in added_enum:
                joined[item.name] = item.value
        return enum.Enum(added_enum.__name__, joined)

    return wrapper


def method_allowed_roles(role_names: List[str]):
    """
    @method_allowed_roles(viewset_allowed_roles(["user"]))
    def perm_required(self, request, *args, **kwargs):
        pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if request.user and ((set(request.user.role_names) & set(role_names)) or request.scene in role_names):
                raise PermissionDenied("当前角色不支持该功能")
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def viewset_allowed_roles(role_names: List):
    """
    @method_decorator(viewset_allowed_roles(["user"]), name="list")
    class xxxViewset:
        pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.user and ((set(request.user.role_names) & set(role_names)) or request.scene in role_names):
                return func(request, *args, **kwargs)
            raise PermissionDenied("当前角色不支持该功能")

        return wrapper

    return decorator
