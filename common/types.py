import enum

from rest_framework.serializers import Serializer


class MyEnum(enum.Enum):
    @classmethod
    def dict(cls):
        return {item.value: item.label for item in cls}

    @classmethod
    def labels(cls):
        return [item.label for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]

    @classmethod
    def choices(cls):
        return [(item.value, item.label) for item in cls]


class IntEnumMore(int, MyEnum):
    def __new__(cls, value, label):
        obj = int.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj


class StrEnumMore(str, MyEnum):
    def __new__(cls, value, label):
        obj = str.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj


class Map(dict):
    """
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """

    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]


class RequestSchema(Serializer):
    def create(self, validated_data):
        raise RuntimeError("Just for request schema")

    def update(self, instance, validated_data):
        raise RuntimeError("Just for request schema")


@enum.unique
class RequestMethodEnum(enum.Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    OPTIONS = "options"
    HEAD = "head"
    CONNECT = "connect"
    TRACE = "trace"


@enum.unique
class ContentTypeEnum(enum.Enum):
    APPlICATION_JSON = "application/json"
    MULTIPART_FORM_DATA = "multipart/form-data"
    APPlICATION_JSON_X_FORM_URLENCODE = "application/x-www-form-urlencoded"
