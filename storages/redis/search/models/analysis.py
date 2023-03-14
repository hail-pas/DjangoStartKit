from typing import Any, Dict, List, Tuple, Union, Iterable

from common.utils import format_str_to_millseconds
from storages.redis.keys import RedisSearchIndex

from storages.redis.search.base import (  # RSJSONField,; PlainTextField,; PlainNumericTimestampField
    BaseModel,
    RSTextField,
    PlainJSONField,
    RSNumericField,
    PlainChoiceField,
    PlainNumericField,
    RSNumericTimestampField,
)


class ExportMethodMixin:
    @classmethod
    def get_export_filters(cls, export_proxy):
        return [], {}

    # @classmethod
    # def get_export_values(cls, export_proxy, o):
    #     values = []
    #     return values

    @classmethod
    def get_transform_config(self, export_contex: "ExportContextProxy", value_key: str, value):
        config = {
            "cancel": lambda x: "已取消" if x else "未取消",
        }
        if value_key not in config:
            return value
        return config.get(value_key)(value)


class SWTemperatureAnalysis(BaseModel, ExportMethodMixin):
    vin = RSTextField("vin")
    city_id = PlainNumericField("city_id", int)
    first_time = RSNumericTimestampField("first_time", sortable=True)
    truck_status_set = PlainJSONField("truck_status_set")
    charge_status = PlainChoiceField("charge_status", int, ((0, "初始值"), (1, "开始充电"), (2, "充电错误"), (3, "充电结束")))
    bmsdtc_code_map = PlainJSONField("bmsdtc_code_map")
    max_highest_lbc_temperature = RSNumericField("max_highest_lbc_temperature", float, sortable=True, no_index=True)
    min_highest_lbc_temperature = RSNumericField("min_highest_lbc_temperature", float, sortable=True, no_index=True)
    last_highest_lbc_temperature = RSNumericField("last_highest_lbc_temperature", float, sortable=True, no_index=True)
    last_highest_lbc_temperature_number = RSNumericField(
        "last_highest_lbc_temperature_number", float, sortable=True, no_index=True
    )
    vcu_key_sta = PlainChoiceField("vcu_key_sta", int, ((0, "Off"), (1, "On"), (2, "Ready")))
    cancel = PlainJSONField("cancel")
    lat = PlainNumericField("lat", float)
    lng = PlainNumericField("lng", float)

    class Meta:
        prefix = RedisSearchIndex.SWTemperatureAnalysisIndex.value

    @classmethod
    def after_serialize(cls, data: Union[List[Dict], Dict], single: bool = False):
        if single:
            data = [data]
        for d in data:
            # 结构号固定为：M3EV
            d["hirhierarchy_num"] = "M3EV"
            # 车辆状态展示
            cls.truck_status_set_display_handle(d)

        if single:
            return data[0]
        return data

    @classmethod
    def truck_status_set_display_handle(cls, d):
        converter = {
            1: "启动状态",
            2: "熄火状态",
            3: "其他状态",
        }
        display = []
        for i in d.get("truck_status_set") or []:
            if i in converter.keys():
                display.append(converter.get(i))
        d["truck_status_set_display"] = ", ".join(display)
        return d
