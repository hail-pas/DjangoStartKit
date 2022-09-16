import binascii
from typing import Any, Dict, List, Type, Tuple, Union, Callable
from contextlib import contextmanager

from ujson import loads
from drf_yasg import openapi
from pydantic import BaseModel as PydanticBaseModel
from happybase import Table, Connection, ConnectionPool
from cachetools.func import lru_cache

from conf.enums import Environment
from conf.config import local_configs
from common.types import Map
from common.utils import get_random_host_and_port


def hbase_connection_pool(size: int = 50, **kwargs) -> ConnectionPool:
    host, port = get_random_host_and_port(local_configs.HBASE.SERVERS)
    pool = ConnectionPool(size=size, host=host, port=int(port), **kwargs)
    return pool


@contextmanager
def hbase_connection(**kwargs):
    if "host" not in kwargs:
        host, port = get_random_host_and_port(local_configs.HBASE.SERVERS)
        kwargs.update(dict(host=host, port=int(port),))
    conn = Connection(**kwargs)
    try:
        yield conn
    finally:
        conn.close()


_RESPONSE_MODEL_INDEX: Dict[str, Type[PydanticBaseModel]] = {}


class BaseModelMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: dict):
        """
        check table name of model
        :param name:
        :param bases:
        :param attrs:
        """
        meta_class: "BaseModel.Meta" = attrs.get("Meta", None)
        if not meta_class:
            raise RuntimeError(f"Must define the meta class of HBase Model - {name}")
        abstract = getattr(meta_class, "abstract", False)
        has_columns = False
        for attr_name, attr in attrs.items():
            if (
                attr_name.startswith("_")
                or attr_name == "Meta"
                or isinstance(attr, classmethod)
                or isinstance(attr, Callable)
            ):
                continue

            if attr_name == "Columns" and attr:
                # 检测 Columns 属性
                if not isinstance(attr, dict):
                    raise RuntimeError(f"Must define Columns field with dict format of HBase Model - {name}")

                for column_name, display in attr.items():
                    if not isinstance(column_name, bytes):
                        raise RuntimeError(
                            f"Must define Columns field key with byte format of HBase Model - {name}, key {column_name} got {type(column_name)}"
                        )
                    if not isinstance(display, str):
                        raise RuntimeError(
                            f"Must define Columns field value with string format of HBase Model - {name}, value {display} got {type(display)}"
                        )

                has_columns = True

        if not has_columns:
            raise RuntimeError(f"Must define Columns field of HBase Model - {name}")

        if not abstract:
            table_name = getattr(meta_class, "table_name", None)
            if not table_name:
                raise RuntimeError(f"Must specify table_name of HBase Model - {name} in Meta class")
            attrs["_table_name"] = table_name
            family_name = getattr(meta_class, "family_name", None)
            # if not column_family_name:
            #     raise RuntimeError(f"Must specify column_family_name of HBase Model - {name} in Meta class")
            attrs["_family_name"] = family_name
            hex_columns = getattr(meta_class, "hex_columns", [])  # type: list
            json_columns = getattr(meta_class, "json_columns", [])  # type: list
            json_column_mapper = getattr(meta_class, "json_column_mapper", {})  # type: dict
            for base in bases:
                _parent_hex_columns = getattr(base, "_hex_columns", None)
                _parent_json_columns = getattr(base, "_json_columns", None)
                _parent_json_column_mapper = getattr(base, "_json_column_mapper", None)
                if _parent_hex_columns:
                    hex_columns.extend(_parent_hex_columns)
                if _parent_json_columns:
                    json_columns.extend(_parent_json_columns)
                if _parent_json_column_mapper:
                    json_column_mapper.update(_parent_json_column_mapper)

            attrs["_hex_columns"] = hex_columns
            attrs["_json_columns"] = json_columns
            attrs["_json_column_mapper"] = json_column_mapper
        return super().__new__(mcs, name, bases, attrs)

    @property
    @lru_cache
    def response_model(cls, is_list: bool = True):
        properties = {}
        json_column_mapper = cls.__json_column_mapper  # noqa
        for k, display in cls.Columns.items():  # noqa
            if k in cls._json_columns and k in json_fields_mapper:  # noqa
                in_properties = {}
                for (in_k, desc) in json_column_mapper.get(k, (None, []))[1]:
                    in_properties[in_k] = openapi.Schema(type=openapi.TYPE_STRING, default="", description=desc)
                properties[k] = openapi.Schema(
                    type=openapi.TYPE_OBJECT, properties=in_properties, description=f"{k}字段结构"
                )
            else:
                properties[k] = openapi.Schema(type=openapi.TYPE_STRING, default="", description=display)

        data_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT, properties=properties, description=f"{cls.__name__}单数据响应体结构"
        )

        if is_list:
            data_schema = openapi.Schema(
                type=openapi.TYPE_ARRAY, items=data_schema, description=f"{cls.__name__}列表响应体结构"
            )

        properties = {
            "code": openapi.Schema(type=openapi.TYPE_INTEGER, default=0, description="业务状态码"),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True, description="是否成功"),
            "message": openapi.Schema(type=openapi.TYPE_STRING, default="", description="提示信息"),
            "data": data_schema,
        }
        rest_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT, properties=properties, description=f"{cls.__name__}响应体结构"
        )

        return rest_schema

    @property
    @lru_cache
    def table_prefix(cls):
        env_to_table_prefix = {
            Environment.development.value: "dev",
            Environment.test.value: "test",
            Environment.production.value: "pro",
        }
        return env_to_table_prefix[local_configs.PROJECT.ENVIRONMENT]


class BaseModel(metaclass=BaseModelMeta):
    """
    Table -> Row Key -> Column Family -> Column ==> Value

    Table
        - RowKey1
            - {ColumnFamilyA:Column = Value1}
            - {ColumnFamilyB:Column = Value2}
        - RowKey2
            - {ColumnFamilyA:Column = Value3}
            - {ColumnFamilyB:Column = Value4}
    """

    _pool = None
    _table_name = None
    _family_name = None
    _hex_columns = []
    _json_columns = []
    _json_column_mapper = {}

    class Meta:
        abstract = True
        table_name = None

    @classmethod
    def value_decode(cls, column_name, value):
        if isinstance(value, bytes):
            try:
                if column_name in cls._hex_columns:
                    value = binascii.hexlify(value).decode()
                elif column_name in cls._json_columns:
                    value = loads(value.decode())
                else:
                    value = value.decode()
            except UnicodeDecodeError:
                value = str(value)
        return value

    @classmethod
    def column_range_map(cls):
        raise NotImplementedError
        # 左闭右闭
        # map = {
        #     "A:a01": [0, 252], "A:a02": [1, 2], "A:a03": [1, 2], "A:a04": [1, 2], "A:a05": [1, 2],
        #     "A:a06": [0, 1], "A:a07": [0, 1], "A:a08": [0, 3], "A:a09": [0, 9], "A:a10": [0, 3],
        #     "A:a11": [0, 3], "A:a12": [1, 6], "A:a13": [0, 32768], "A:a14": [0, 32768], "A:a15": [0, 2000],
        #     "A:a16": [-327, 327], "A:a17": [0, 8], "A:a18": [1, 50], "A:a19": [51, 255], "A:a20": [0, 3],
        #     "A:a21": [0, 200], "A:a22": [0, 200], "A:a23": [0, 100], "A:a24": [0, 100],
        #     "A:a25": [-40, 210], "A:a26": [0, 2000], "A:a27": [-1000, 1000], "A:a28": [0, 25.4], "A:a29": [-40, 210],
        #     "A:a30": [0, 4095], "A:a31": [0, 250], "A:a32": [0, 15], "A:a33": [0, 250], "A:a34": [0, 15],
        #     "A:a35": [0, 250], "A:a36": [-40, 210], "A:a37": [0, 250], "A:a38": [-40, 210], "A:a39": [3, 4],
        # }
        # return map

    @classmethod
    def data_clean(cls, data: Union[List, Dict]):
        if isinstance(data, dict):
            return cls.column_clean(data)
        elif isinstance(data, (tuple, list)):
            result = []
            for d in data:
                if isinstance(d, dict):
                    result.append(cls.column_clean(d))
            return result
        else:
            raise RuntimeError(f"Not Supported Data Type - {type(data)}")

    @classmethod
    def column_clean(
        cls,
        single_data: dict,
        place_holder: str = "-",
        keep_original: bool = True,
        customize_display: Callable[[Any], str] = None,
    ) -> dict:
        """
        customize_display = lambda v: {"-65534": "无效", "-65535": "异常"}.get(v)
        """
        result = {}
        for k, v in single_data.items():
            result[k] = v
            defined_range = cls.column_range_map().get(k)
            try:
                if defined_range and not defined_range[0] <= float(v) <= defined_range[1]:
                    result[k] = place_holder
                    if keep_original:
                        result[f"{k}__original"] = v
                    if customize_display:
                        result[k] = customize_display(v)
            except Exception:  # noqa
                pass
        return result

    @classmethod
    def serialize(cls, retrieved_data: Union[list, dict]):
        if isinstance(retrieved_data, dict):
            item = {}
            for k, v in retrieved_data.items():
                item[k.decode("utf-8")] = cls.value_decode(k, v)
            return item
        result = []
        for row_key, hbase_data in retrieved_data:
            item = {"row_key": row_key.decode()}
            for k, v in hbase_data.items():
                item[k.decode("utf-8")] = cls.value_decode(k, v)
            result.append(Map(item))
        return result

    @classmethod
    def scan(
        cls,
        row_start: str = None,
        row_stop: str = None,
        row_prefix: bytes = None,
        columns: List[str] = None,
        filter: str = None,  # noqa
        timestamp: int = None,
        include_timestamp: bool = False,
        batch_size: int = 1000,
        scan_batching: bool = None,
        limit=None,
        sorted_columns: bool = False,
        reverse: bool = False,
        specify_table_name: str = None,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            data = table.scan(
                row_start=row_start,
                row_stop=row_stop,
                row_prefix=row_prefix,  # noqa
                columns=columns,
                filter=filter,
                timestamp=timestamp,
                include_timestamp=include_timestamp,
                batch_size=batch_size,
                scan_batching=scan_batching,
                limit=limit,
                sorted_columns=sorted_columns,
                reverse=reverse,
            )
            return cls.serialize(data)

    @classmethod
    def row(
        cls,
        row: str,
        columns: List[Union[str, bytes]] = None,
        timestamp: int = None,
        include_timestamp: bool = False,
        serialize_fnc: Callable = None,
        specify_table_name: str = None,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            result = table.row(row, columns=columns, timestamp=timestamp, include_timestamp=include_timestamp)
            if result:
                result = cls.serialize(result)
                result["row_key"] = row
                if serialize_fnc:
                    result = serialize_fnc(result)
            return result

    @classmethod
    def rows(
        cls,
        rows: List[str],
        columns: List[str] = None,
        timestamp: int = None,
        include_timestamp=False,
        specify_table_name: str = None,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            data = table.rows(rows, columns=columns, timestamp=timestamp, include_timestamp=include_timestamp)
            return cls.serialize(data)

    @classmethod
    def put(
        cls, row: str, data: dict, timestamp: int = None, wal: bool = True, specify_table_name: str = None,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            table.put(row, data, timestamp=timestamp, wal=wal)
