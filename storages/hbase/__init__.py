from typing import Dict, List, Type, Tuple, Union
from contextlib import contextmanager

from pydantic import BaseModel as PydanticBaseModel
from pydantic import create_model
from happybase import Table, Connection, ConnectionPool

from common.utils import get_random_host_and_port
from conf.config import local_configs
from common.types import Map


def hbase_connection_pool(size: int = 10, **kwargs) -> ConnectionPool:
    host, port = get_random_host_and_port(local_configs.THRIFT_SERVERS)
    pool = ConnectionPool(size=size, host=host, port=port, **kwargs)
    return pool


@contextmanager
def hbase_connection(**kwargs):
    host, port = get_random_host_and_port(local_configs.THRIFT_SERVERS)
    conn = Connection(host=host, port=port, **kwargs)
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
        if not abstract:
            table_name = getattr(meta_class, "table_name", None)
            if not table_name:
                raise RuntimeError(f"Must specify table_name of HBase Model - {name} in Meta class")
            attrs["_table_name"] = table_name
            bytes_to_str_map = {}
            for k, v in attrs.items():
                if isinstance(v, bytes):
                    bytes_to_str_map[v] = k
            if not bytes_to_str_map:
                raise RuntimeError(f"Must define one column at least of HBase Model - {name}")
            attrs["_bytes_to_str_map"] = bytes_to_str_map
        return super().__new__(mcs, name, bases, attrs)

    @property
    def response_model(cls):
        model_name = f"Hbase.{cls.__name__}"
        if _RESPONSE_MODEL_INDEX.get(model_name):
            return _RESPONSE_MODEL_INDEX[model_name]

        attrs = {}
        for _, field_name in cls._bytes_to_str_map.items():
            attrs[field_name] = (str, None)

        _RESPONSE_MODEL_INDEX[model_name] = create_model(model_name, **attrs)

        return _RESPONSE_MODEL_INDEX[model_name]


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
    _bytes_to_str_map = None

    class Meta:
        abstract = True
        table_name = None

    @classmethod
    def serialize(cls, retrieved_data):
        result = []
        for row_key, hbase_data in retrieved_data:
            item = {"row_key": row_key}
            for k, v in cls._bytes_to_str_map.items():
                value = hbase_data.get(k)
                if isinstance(value, bytes):
                    value = value.decode()
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
            limit: int = None,
            sorted_columns: bool = False,
            reverse: bool = False,
    ):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        columns = [field if isinstance(field, bytes) else cls.__dict__[field] for field in columns]
        with cls._pool.connection() as conn:
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
    def row(cls, row: str, columns: List[Union[str, bytes]] = None, timestamp: int = None,
            include_timestamp: bool = False):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        columns = [field if isinstance(field, bytes) else cls.__dict__[field] for field in columns]
        with cls._pool.connection() as conn:
            table = conn.table(cls._table_name)  # type: Table
            data = table.row(row, columns=columns, timestamp=timestamp, include_timestamp=include_timestamp)
            result = cls.serialize(data)
            return result[0] if result else None

    @classmethod
    def rows(cls, rows: List[str], columns: List[str] = None, timestamp: int = None, include_timestamp=False):
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        columns = [field if isinstance(field, bytes) else cls.__dict__[field] for field in columns]
        with cls._pool.connection() as conn:
            table = conn.table(cls._table_name)  # type: Table
            data = table.rows(rows, columns=columns, timestamp=timestamp, include_timestamp=include_timestamp)
            return cls.serialize(data)

    @classmethod
    def put(cls, row: str, data: dict, timestamp: int = None, wal: bool = True):
        parsed_data = {}
        for k, v in data.items():
            parsed_data[getattr(cls, k)] = v.encode("utf-8")
        if cls._pool is None:
            cls._pool = hbase_connection_pool()
        with cls._pool.connection() as conn:
            table = conn.table(cls._table_name)  # type: Table
            table.put(row, parsed_data, timestamp=timestamp, wal=wal)
