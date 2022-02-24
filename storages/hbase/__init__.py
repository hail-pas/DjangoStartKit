import binascii
from typing import Dict, List, Type, Tuple, Union, Callable
from contextlib import contextmanager

from cachetools.func import lru_cache
from drf_yasg import openapi
from pydantic import BaseModel as PydanticBaseModel
from happybase import Table, Connection, ConnectionPool
from ujson import loads

from common.utils import get_random_host_and_port
from conf.config import local_configs
from common.types import Map
from conf.enums import Environment


def hbase_connection_pool(size: int = 50, **kwargs) -> ConnectionPool:
    host, port = get_random_host_and_port(local_configs.THRIFT_SERVERS)
    pool = ConnectionPool(size=size, host=host, port=int(port), **kwargs)
    return pool


@contextmanager
def hbase_connection(**kwargs):
    if "host" not in kwargs:
        host, port = get_random_host_and_port(local_configs.THRIFT_SERVERS)
        kwargs.update(dict(host=host, port=int(port), ))
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
            raise RuntimeError(f"Must define the meta class of HBase Model - {name} with table_name field")
        abstract = getattr(meta_class, "abstract", False)
        for _, attr in attrs.items():
            if _.startswith("_") or _ == "Meta" or isinstance(attr, classmethod):
                continue
            assert isinstance(attr, (list, tuple)) and len(attr) == 2, f"{_} 必须使用('column_name', 'verbose_name')"
            assert isinstance(attr[0], (str, bytes)) and isinstance(attr[1],
                                                                    str), f"{_} 使用 str 或 bytes 类型指定 column_name, 使用 str 指定 verbose_name"  # noqa
        if not abstract:
            table_name = getattr(meta_class, "table_name", None)
            if not table_name:
                raise RuntimeError(f"Must specify table_name of HBase Model - {name} in Meta class")
            attrs["_table_name"] = table_name
            column_family_name = getattr(meta_class, "column_family_name", None)
            # if not column_family_name:
            #     raise RuntimeError(f"Must specify column_family_name of HBase Model - {name} in Meta class")
            attrs["_column_family_name"] = column_family_name
            bytes_to_str_map = {}
            fields_map = {}
            hex_fields = getattr(meta_class, "hex_fields", [])  # type: list
            json_fields = getattr(meta_class, "json_fields", [])  # type: list
            json_fields_mapper = getattr(meta_class, "json_fields_mapper", {})  # type: dict
            for k, v in attrs.items():
                if k.startswith("_") or k == "Meta" or isinstance(v, classmethod):
                    continue
                if isinstance(v[0], bytes):
                    # 指定为bytes类型则直接使用
                    bytes_to_str_map[v[0]] = k
                    fields_map[k] = v[1]
                else:
                    # 组装 column_family_name 和 column_name
                    if not column_family_name:
                        raise RuntimeError(f"Must specify column_family_name of HBase Model - {name} in Meta class")
                    bytes_to_str_map[f"{column_family_name}:{v[0]}".encode()] = k
            for base in bases:
                _parent_bytes_to_str_map = getattr(base, "_bytes_to_str_map", None)
                _parent_hex_fields = getattr(base, "_hex_fields", None)
                _parent_json_fields = getattr(base, "_json_fields", None)
                _parent_json_fields_mapper = getattr(base, "_json_fields_mapper", None)
                _parent_fields_map = getattr(base, "_fields_map")
                if _parent_bytes_to_str_map:
                    bytes_to_str_map.update(_parent_bytes_to_str_map)
                    fields_map.update(_parent_fields_map)
                if _parent_hex_fields:
                    hex_fields.extend(_parent_hex_fields)
                if _parent_json_fields:
                    json_fields.extend(_parent_json_fields)
                if _parent_json_fields_mapper:
                    json_fields_mapper.update(_parent_json_fields_mapper)

            attrs["_hex_fields"] = hex_fields
            attrs["_json_fields"] = json_fields
            attrs["_json_fields_mapper"] = json_fields_mapper

            if not bytes_to_str_map:
                raise RuntimeError(f"Must define one column at least of HBase Model - {name}")
            attrs["_bytes_to_str_map"] = bytes_to_str_map
            attrs["_str_to_bytes_map"] = {v: k for k, v in bytes_to_str_map.items()}
            attrs["_fields_map"] = fields_map
        return super().__new__(mcs, name, bases, attrs)

    @property
    @lru_cache
    def response_model(cls, is_list: bool = True):
        properties = {
        }
        json_fields_mapper = cls._json_fields_mapper
        for k, _ in cls._str_to_bytes_map.items():
            if k in cls._json_fields and k in json_fields_mapper:
                in_properties = {}
                for (in_k, desc) in json_fields_mapper.get(k):
                    in_properties[in_k] = openapi.Schema(type=openapi.TYPE_STRING, default="", description=desc)
                properties[k] = openapi.Schema(type=openapi.TYPE_OBJECT, properties=in_properties,
                                               description=f"{k}字段结构")
            else:
                properties[k] = openapi.Schema(type=openapi.TYPE_STRING, default="", description=getattr(cls, k)[1])

        data_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=properties,
            description=f"{cls.__name__}单数据响应体结构"
        )

        if is_list:
            data_schema = openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=data_schema,
                description=f"{cls.__name__}列表响应体结构"
            )

        properties = {
            "code": openapi.Schema(type=openapi.TYPE_INTEGER, default=100200, description="业务状态码"),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True, description="是否成功"),
            "message": openapi.Schema(type=openapi.TYPE_STRING, default="", description="提示信息"),
            "data": data_schema,
        }
        rest_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=properties,
            description=f"{cls.__name__}响应体结构"
        )

        return rest_schema

    @property
    @lru_cache
    def table_prefix(cls):
        env_to_table_prefix = {
            Environment.development.value: "dev",
            Environment.test.value: "test",
            Environment.production.value: "pro"
        }
        return env_to_table_prefix[local_configs.ENVIRONMENT]


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
    _column_family_name = None
    _bytes_to_str_map = None
    _str_to_bytes_map = None
    _hex_fields = []
    _json_fields = []
    _json_fields_mapper = {}
    _fields_map = None

    class Meta:
        abstract = True
        table_name = None

    @classmethod
    def serialize(cls, retrieved_data: Union[list, dict]):
        if isinstance(retrieved_data, dict):
            item = {}
            for k, v in cls._bytes_to_str_map.items():
                value = retrieved_data.get(k)
                if isinstance(value, bytes):
                    try:
                        if v in cls._hex_fields:
                            value = binascii.hexlify(value).decode()
                        elif v in cls._json_fields:
                            value = loads(value.decode())
                        else:
                            value = value.decode()
                    except UnicodeDecodeError:
                        value = str(value)
                item[v] = value
            return item
        result = []
        for row_key, hbase_data in retrieved_data:
            item = {"row_key": row_key.decode()}
            for k, v in cls._bytes_to_str_map.items():
                value = hbase_data.get(k)
                if not value:
                    continue
                if isinstance(value, bytes):
                    try:
                        if v in cls._hex_fields:
                            value = binascii.hexlify(value).decode()
                        elif v in cls._json_fields:
                            value = loads(value.decode())
                        else:
                            value = value.decode()
                    except UnicodeDecodeError:
                        value = str(value)
                item[v] = value
            result.append(Map(item))
        return result

    @classmethod
    def scan(
            cls,
            row_start: str = None,
            row_stop: str = None,
            row_prefix: str = None,
            columns: List[str] = None,
            filter: str = None,
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
        if columns:
            columns = [field if isinstance(field, bytes) else cls._str_to_bytes_map[field] for field in columns]
        else:
            columns = list(cls._bytes_to_str_map.keys())
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            data = table.scan(
                row_start=row_start,
                row_stop=row_stop,
                row_prefix=row_prefix,
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
        if columns:
            columns = [field if isinstance(field, bytes) else cls._str_to_bytes_map[field] for field in columns]
        else:
            columns = list(cls._bytes_to_str_map.keys())
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
        if columns:
            columns = [field if isinstance(field, bytes) else cls._str_to_bytes_map[field] for field in columns]
        else:
            columns = list(cls._bytes_to_str_map.keys())
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            data = table.rows(rows, columns=columns, timestamp=timestamp, include_timestamp=include_timestamp)
            return cls.serialize(data)

    @classmethod
    def put(
            cls,
            row: str,
            data: dict,
            timestamp: int = None,
            wal: bool = True,
            specify_table_name: str = None,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            if specify_table_name:
                table = conn.table(specify_table_name)  # type: Table
            else:
                table = conn.table(cls._table_name)  # type: Table
            table.put(row, data, timestamp=timestamp, wal=wal)
