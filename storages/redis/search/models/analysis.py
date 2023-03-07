from typing import Any, Dict, List, Tuple, Iterable

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
    def get_iterate_data(cls, export_proxy):
        param = export_proxy.history.params
        min_first_time = param.get("first_time__gte")
        max_first_time = param.get("first_time__lte")
        min_first_time = format_str_to_millseconds(min_first_time) if min_first_time else ""
        max_first_time = format_str_to_millseconds(max_first_time) if max_first_time else ""
        vin = param.get("vin")
        first_alert_time_query = f"[{min_first_time if min_first_time else float('-inf')} {max_first_time if max_first_time else float('inf')}]"
        query_string = f"@first_time:{first_alert_time_query}"
        if vin:
            query_string += f" & @vin:{vin}*"
        # _filter_query_string = generate_on_going_query_string(
        # request.user
        # )
        # if _filter_query_string:
        # query_string += f" & {_filter_query_string}"
        result = cls.objects.filter(query_string=query_string)
        return cls.after_serialize(cls.serialize(result.docs))

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
    def after_serialize(cls, data: List[Dict]):
        for d in data:
            # 额外字段处理
            d["hirhierarchy_num"] = "M3EV"

        return data
