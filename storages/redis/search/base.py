from enum import Enum
from typing import Any, Dict, List, Type, Tuple, Union, Callable, Iterable

import ujson
from redis import Redis, ResponseError
from redisearch import (
    Query,
    Client,
    Result,
    Document,
    TagField,
    GeoFilter,
    TextField,
    NumericField,
    NumericFilter,
    IndexDefinition,
)

from common.utils import millseconds_to_format_str
from storages.redis import RedisUtil
from storages.redis.keys import RedisSearchIndex


class Serializeable:
    def to_python_value(self, v):
        return v

    def to_db_value(self, v):
        raise v


class RSTagField(Serializeable, TagField):
    def __init__(self, name, separator=",", **kwargs):
        super().__init__(name, separator, **kwargs)


class RSTextField(Serializeable, TextField):
    pass


class RSNumericField(Serializeable, NumericField):
    type_: Type

    def __init__(self, name, type: Type, **kwargs):
        super().__init__(name, **kwargs)
        self.type_ = type

    def to_python_value(self, v):
        if v:
            try:
                return self.type_(v)
            except Exception:
                return v

    def to_db_value(self, v):
        return v


class RSNumericTimestampField(Serializeable, NumericField):
    type_: Type = int
    offset: int = 1000

    def __init__(self, name, offset: int = 1000, **kwargs):
        super().__init__(name, **kwargs)
        self.type_ = int
        self.offset = offset

    def to_python_value(self, v):
        if v:
            try:
                return millseconds_to_format_str(self.type_(v) / self.offset * 1000)
            except Exception:
                return v

    def to_db_value(self, v):
        return v


class JSONTransMethodMixin(Serializeable):
    def to_python_value(self, strs):
        if strs:
            try:
                return ujson.loads(strs)
            except Exception:
                return strs

    def to_db_value(self, obj):
        if obj:
            return ujson.dumps(obj)
        return ""


class ChoiceField(Serializeable):
    choices: Tuple
    type_: Type

    def to_python_value(self, v):
        if v is not None:
            try:
                return self.type_(v)
            except Exception:
                pass
        return v

    def display(self, v):
        if not v:
            return v
        return dict(self.choices).get(self.to_python_value(v), v)


class RSTextChoiceField(ChoiceField, TextField):
    type_: Type = str

    def __init__(self, name, choices: Enum, weight=1, no_stem=False, phonetic_matcher=None, **kwargs):
        super().__init__(name, weight, no_stem, phonetic_matcher, **kwargs)
        self.choices = choices


class RSJSONField(
    TextField, JSONTransMethodMixin,
):
    def __init__(self, name, weight=1, no_stem=False, phonetic_matcher=None, **kwargs):
        super().__init__(name, weight, no_stem, phonetic_matcher, **kwargs)


class RSNumericChoiceField(
    ChoiceField, NumericField,
):
    type_: Type

    def __init__(self, name, type_, choices: Enum, **kwargs):
        super().__init__(name, **kwargs)
        self.choices = choices
        self.type_ = type_


class PlainField:
    _description: str = "Simple Plain Cache Fields"


class PlainJSONField(
    JSONTransMethodMixin, PlainField,
):
    name: str

    def __init__(self, name) -> None:
        self.name = name


class PlainTextField(PlainField, Serializeable):
    def __init__(self, name) -> None:
        self.name = name


class PlainNumericField(PlainField, Serializeable):
    type_: Type

    def __init__(self, name, type_: Type) -> None:
        self.name = name
        self.type_ = type_

    def to_python_value(self, v):
        if v:
            try:
                return self.type_(v)
            except Exception:
                pass
        return v


class PlainNumericTimestampField(PlainField, Serializeable):
    type_: Type = int
    offset: int = 1000

    def __init__(self, name, offset: int = 1000, **kwargs):
        self.type_ = int
        self.offset = offset

    def to_python_value(self, v):
        if v:
            try:
                return millseconds_to_format_str(self.type_(v) / self.offset * 1000)
            except Exception:
                return v

    def to_db_value(self, v):
        return v


class PlainChoiceField(ChoiceField, PlainField):
    name: str
    choices: Enum
    type_: Type

    def __init__(self, name, type_: Type, choices: Enum) -> None:
        self.name = name
        self.type_ = type_
        self.choices = choices


class RSManger:
    # redis 实例
    redis: Redis
    client: Client

    def __init__(self, prefix: RedisSearchIndex, r: Redis = None) -> None:
        self.redis = r
        if not self.redis:
            self.redis = Redis(connection_pool=RedisUtil.get_pool(0))  # 必须使用 0
        self.client = Client(prefix, conn=self.redis)

    def filter(
        self,
        query_string: str = "*",
        start: int = 0,
        limit: int = 0,
        return_fields: List = [],
        filters: Tuple[Union[NumericFilter, GeoFilter]] = [],
        sort_by: Tuple[Union[str, bool]] = None,
    ) -> Result:
        # 1. Query(query_string)
        # &: and
        # |: or
        # -: not
        # 2. paging(start, limit)
        # 3. sort_by("field", asc=False)
        query: Query = Query(query_string).return_fields(*return_fields)
        for f in filters:
            query.add_filter(f)
        if not limit:
            query.paging(0, 1)
            # AggregateRequest(query_string).group_by([], reducers.count())
            limit = self.client.search(query).total
        query.paging(start, limit)
        if sort_by:
            query.sort_by(*sort_by)
        result = self.client.search(query)
        return result


class BaseModelMeta(type):
    _field_names: List
    _field_values: List
    _plain_fields: List
    _index_fields: List
    _prefix: str
    objects: RSManger

    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: dict):
        """
        :param name:
        :param bases:
        :param attrs:
        """
        meta_class: "BaseModel.Meta" = attrs.get("Meta", None)
        if not meta_class:
            raise RuntimeError(f"Must define the meta class of HBase Model - {name}")
        abstract = getattr(meta_class, "abstract", False)
        field_names = []
        field_values = []
        plain_fields = []
        index_fields = []
        for attr_name, attr in attrs.items():
            if (
                attr_name.startswith("_")
                or attr_name == "Meta"
                or isinstance(attr, classmethod)
                or isinstance(attr, Callable)
            ):
                continue
            if isinstance(attr, PlainField):
                plain_fields.append(attr_name)
            else:
                index_fields.append(attr_name)
            field_names.append(attr_name)
            field_values.append(attr)

        if not field_names and not abstract:
            raise RuntimeError(f"Must define field of Non-Abstract Model - {name}")

        if not abstract:
            prefix = getattr(meta_class, "prefix", None)
            if not prefix:
                raise RuntimeError(f"Must specify prefix of Model - {name} in Meta class")
            attrs["_prefix"] = prefix
            attrs["objects"] = RSManger(prefix)
            for base in bases:
                _parent_field_names = getattr(base, "_field_names", None)
                _parent_field_values = getattr(base, "_field_values", None)
                _parent_plain_fields = getattr(base, "_plain_fields", None)
                _parent_index_fields = getattr(base, "_index_fields", None)
                if _parent_field_names:
                    field_names.extend(_parent_field_names)
                if _parent_field_values:
                    field_values.extend(_parent_field_values)
                if _parent_plain_fields:
                    plain_fields.extend(_parent_plain_fields)
                if _parent_index_fields:
                    index_fields.extend(_parent_index_fields)

            attrs["_field_names"] = field_names
            attrs["_field_values"] = field_values
            attrs["_plain_fields"] = plain_fields
            attrs["_index_fields"] = index_fields

        return super().__new__(mcs, name, bases, attrs)


class BaseModel(metaclass=BaseModelMeta):
    class Meta:
        # prefix = RedisSearchIndex.SWTemperatureAnalysisIndex.value  # Use Case: IndexName -> PIndex; Hash Key -> P:xxxx
        abstract = True

    @classmethod
    def create_index(cls):
        definition = IndexDefinition(prefix=[cls._prefix])
        schema = list(filter(lambda x: x.name in cls._index_fields, cls._field_values))
        try:
            print(cls.objects.client.info())
        except ResponseError:
            # Index does not exist. We need to create it!
            print(f"Creating {cls._prefix}... \n")
            cls.objects.client.create_index(schema, definition=definition)
            print(cls.objects.client.info(), "\n")

    @classmethod
    def drop_index(cls):
        cls.objects.client.dropindex(delete_documents=False)
        print(f"Dropped {cls._prefix}... \n")

    @classmethod
    def serialize(cls, data: List[Document]):
        result = []
        fields_map = dict(zip(cls._field_names, cls._field_values))
        for d in data:
            d = d.__dict__
            temp = {"id": d["id"]}
            for key, field in fields_map.items():
                temp[key] = field.to_python_value(d.get(key))
                if isinstance(field, ChoiceField):
                    temp[f"get_{key}_display"] = field.display(d.get(key))

            result.append(temp)

        return cls.after_serialize(result)

    @classmethod
    def after_serialize(cls, data: List[Dict]):
        return data
