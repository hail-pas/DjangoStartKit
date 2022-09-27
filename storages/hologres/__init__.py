import re
import json
import logging
from typing import List, Type, Tuple, Callable

from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from django.db.models import Model

from conf.config import local_configs

logger = logging.getLogger("storages.hologres")  # noqa

try:

    holo_pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        user=local_configs.HOLOGRES.USERNAME,
        password=local_configs.HOLOGRES.PASSWORD,
        host=local_configs.HOLOGRES.HOST,
        port=local_configs.HOLOGRES.PORT,
        database=local_configs.HOLOGRES.DB,
        connect_timeout=local_configs.HOLOGRES.TIMEOUT,
    )
except Exception as e:
    logger.warning(f"创建Hologres连接池失败: {repr(e)}")  # noqa
    holo_pool = None


def select(sql: str):
    ps_connection = holo_pool.getconn()
    try:
        with ps_connection.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql)
            results = cur.fetchall()
            return results
    finally:
        holo_pool.putconn(ps_connection)


class ChoiceFiled:
    choices = None
    display_table = {}

    def __init__(self, choices):
        self.choices = choices
        self.display_table = dict(choices)

    def value(self, key):
        return self.display_table.get(key)


class ForeignField:
    related_model: Model = None
    alias: str = None
    display_related_field_names = []

    def __init__(self, related_model, alias, display_related_field_names: List[str] = None):
        self.alias = alias
        self.related_model = related_model
        if display_related_field_names:
            self.display_related_field_names = display_related_field_names

    def value(self, pk):
        if not pk or not self.display_related_field_names:
            return {}
        target = self.related_model.objects.filter(pk=pk).values(*self.display_related_field_names).first()
        if not target:
            return {}
        return target


class QueryMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: dict):
        meta_class = attrs.get("Meta", None)
        if not meta_class:

            class Meta:
                table_name = re.sub("(?<!^)(?=[A-Z])", "_", name).lower()

            attrs["Meta"] = Meta
        _fields = []
        for k, v in attrs.items():
            _fields.append(k)
        attrs["_fields"] = _fields
        return super().__new__(mcs, name, bases, attrs)

    @property
    def objects(cls) -> "Query":
        return Query(cls)


class HologresQueryModel(metaclass=QueryMeta):  # noqa
    """

    """

    objects: "Query"

    class Meta:
        abstract = True


class Operator:
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"
    NOT = "not"

    table = {
        GTE: ">=",
        GT: ">",
        LTE: "<=",
        LT: "<",
        NOT: "!=",
    }

    @classmethod
    def characterize(cls, operator: str):
        return cls.table.get(operator.lower())


class Query:
    model: HologresQueryModel = None
    filter_kwargs: dict = None
    value_list: Tuple = None
    order_by_values: str = None
    limit_num: int = None
    offset_num: int = None
    serialize_func: Callable[[dict], dict] = None

    def __init__(self, model):
        self.model = model

    def filter(self, **kwargs):
        self.filter_kwargs = kwargs
        return self

    def values(self, *value_list):
        self.value_list = value_list
        return self

    def order_by(self, order_by_values):
        self.order_by_values = order_by_values
        return self

    def limit(self, limit_num):
        self.limit_num = limit_num
        return self

    def offset(self, offset_num):
        self.offset_num = offset_num
        return self

    def sql(self):
        sql_text = "SELECT {} FROM {} WHERE 1=1".format(  # noqa
            ",".join(self.value_list) if self.value_list else "*", self.model.Meta.table_name  # noqa
        )
        sql_text += self.gen_filter_sql()
        if self.order_by_values:
            sql_text += " ORDER BY "
            for order_by_value in self.order_by_values.split(","):
                order_by_value = order_by_value.strip()
                sql_text += "{} {}, ".format(
                    order_by_value.split("-")[-1], "DESC" if order_by_value.startswith("-") else "ASC"
                )

        if self.limit_num is not None and self.offset_num is not None:
            sql_text += " LIMIT {} OFFSET {}".format(self.limit_num, self.offset_num)
        return sql_text

    def serializer(self, serialize_func: Callable[[dict], dict]):
        self.serialize_func = serialize_func
        return self

    def serialize(self, item):
        result = dict(item)
        if self.serialize_func:
            result = self.serialize_func(result)
        for key in self.model._fields:  # noqa
            type_ = getattr(self.model, key, None)
            if isinstance(type_, ChoiceFiled):
                result[key] = type_.value(result[key])
            elif isinstance(type_, ForeignField):
                for k, v in type_.value(result[key]).items():
                    result[type_.alias + "__" + k] = v
            elif isinstance(type_, Callable):
                result[key] = type_(result[key])

        return result

    def query(self):
        return map(self.serialize, select(self.sql()))

    def count(self):
        sql = "SELECT Count(*) FROM {} WHERE 1=1".format(self.model.Meta.table_name) + self.gen_filter_sql()  # noqa
        return select(sql)[0][0]

    def gen_filter_sql(self):
        sql_text = ""
        for key, value in self.filter_kwargs.items():
            if value and isinstance(value, str) and ";" in value:
                raise RuntimeError("Illegal param")
            if "__" in key:
                field_name, operator = key.split("__")
                operator = Operator.characterize(operator)
            else:
                field_name = key
                operator = "="
            # if field_name in self.model.__dict__.keys():
            sql_text += " AND {} {} '{}'".format(field_name, operator, value)
        return sql_text


if __name__ == "__main__":

    class HoloBaseExample:
        id: int
        field1: str
        C_CHOICE = (
            (0, "零"),
            (1, "一"),
        )
        c = ChoiceFiled(C_CHOICE)
        referenced_id: ForeignField(
            related_model="RelatedModel", alias="referenced_name", display_related_field_names=["a", "b"]
        )

        class Meta:
            abstract = True

    class HoloData(HoloBaseExample):
        extra: json.loads
        json: dict

        class Meta:
            table_name = "EXAMPLE_TABLE"

    print(select("SELECT version();"))
