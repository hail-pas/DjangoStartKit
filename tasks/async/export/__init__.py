import os
import csv
import inspect
import logging
from typing import Any, Dict, List, Tuple, Union, Callable, Iterable

from storages import enums

logger = logging.getLogger("tasks.asynchronous.export")


class ExportMethodMixins:
    # Get/Set Context
    @classmethod
    def get_export_filters(cls, export_contex: "ExportContextProxy") -> Tuple[list, dict]:
        raise NotImplementedError

    @classmethod
    def get_export_values(cls, export_contex: "ExportContextProxy", line_o: dict) -> List:
        raise NotImplementedError

    @classmethod
    def get_iterate_data(cls, export_contex: "ExportContextProxy") -> Iterable[Any]:
        raise NotImplementedError

    @classmethod
    def get_transform_config(self, export_contex: "ExportContextProxy", value_key: str):
        raise NotImplementedError


class ExportConfig:
    # Export Config
    headers: List[str]
    value_keys: List[str]
    select_related: Optional[set]
    prefetch_related: Optional[set]
    default_filter_args: Optional[List]
    default_filter_kwargs: Optional[Dict]  # Use Case: *.objects.filter(*default_filter_args, **default_filter_kwargs)

    def __init__(
        self,
        headers: List[List[str]],
        select_related: List = [],
        prefetch_related: List = [],
        default_filter: List[Union[List, Dict]] = [[], {}],
    ) -> None:
        self.select_related = set(select_related)
        self.prefetch_related = set(prefetch_related)
        self.default_filter_args = default_filter[0]
        self.default_filter_kwargs = default_filter[1]
        self.value_keys = [i[1] for i in headers]
        self.headers = [i[0] for i in headers]


class ExportContextProxy(ExportMethodMixins):
    # export context
    writer_pkg = csv
    history: "ExportRecord"  # noqa
    config: ExportConfig
    models_cls: Any
    method_proxy: ExportMethodMixins

    def __init__(
        self,
        writer_pkg: Any,
        config: ExportConfig,
        models_cls: Any,
        method_proxy: ExportMethodMixins,
        history: "ExportRecord",  # noqa
    ) -> None:
        self.writer_pkg = writer_pkg
        self.history = history
        self.config = config
        self.models_cls = models_cls
        self.method_proxy = method_proxy

    def get_export_filters(self) -> Tuple[list, dict]:
        # get cuurent export filters by context
        func = getattr(self.method_proxy, inspect.stack()[0][3], None)
        if func:
            return func(self)
        raise NotImplementedError

    def get_export_values(self, line_data) -> List:
        # get a target line of export data by context and a line of raw data
        func = getattr(self.method_proxy, inspect.stack()[0][3], None)
        if func:
            return func(self, line_data)
        values = []
        for key in self.config.value_keys:
            if isinstance(line_data, dict):
                v = line_data.get(key, "")
            else:
                v = getattr(line_data, key, "")
            if callable(v):
                v = v()
            if v is None:
                v = ""

            if isinstance(v, datetime.datetime):  # v and attr_name in f_map and
                v = v.strftime("%Y-%m-%d %H:%M:%S")

            v = self.get_transform_config(key, v)

            values.append(v)

        return values

    def get_iterate_data(self) -> Iterable[Any]:
        # get iterate data by context
        func = getattr(self.method_proxy, inspect.stack()[0][3], None)
        if func:
            return func(self)
        # default
        args, kwargs = self.get_export_filters()  # get current filters
        return (
            self.models_cls.objects.filter(*self.config.default_filter_args, **self.config.default_filter_kwargs,)
            .filter(*args, **kwargs)
            .select_related(*self.config.select_related,)
            .prefetch_related(*self.config.prefetch_related,)
            .iterator()
        )

    def get_transform_config(self, value_key: str, value):
        func = getattr(self.method_proxy, inspect.stack()[0][3], None)
        if func:
            return func(self, value_key, value)
        # default
        return value

    def export(self, filename_generrator: Callable[["ExportContextProxy", str], str]):
        filename = filename_generrator(self, "csv")
        self.get_writer_handler()(filename)

    def get_writer_handler(self):
        config = {csv: self.csv_write}
        handler = config.get(self.writer_pkg)
        if not handler:
            raise NotImplementedError
        return handler

    def csv_write(self, filename):
        try:
            data = self.get_iterate_data()
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                cw = csv.writer(f)
                cw.writerow(self.config.headers)
                for o in data:
                    temp = self.get_export_values(o)
                    cw.writerow(temp)
        except Exception as e:
            logger.error("Error:{}".format(e), exc_info=True)
            raise e
        else:
            self.history.record_file = os.path.basename(filename)
            self.history.is_complete = enums.IsCompleteEnum.success.value
            self.history.save(update_fields=["record_file", "is_complete"])
            logger.info("export success")
