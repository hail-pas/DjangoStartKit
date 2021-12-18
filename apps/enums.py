"""
全部的Enum类型
"""
import enum
import inspect
import sys
from enum import unique, Enum
from typing import List, Tuple

from common.types import StrEnumMore, IntEnumMore, MyEnum


@unique
class ResponseCodeEnum(IntEnumMore):
    """
    业务响应代码，除了500之外都在200的前提下返回对用code
    """

    # 唯一成功响应
    success = (100200, "成功")

    # HTTP 状态码  2xx - 5xx
    # 100{[2-5]]xx}, http status code 拼接

    # 失败响应，999倒序取
    failed = (100999, "失败")


# class EnumInfoResponseFormats(StrEnumMore):
#     """
#     码表信息响应格式
#     """
#     json_ = ("json", "Json")
#     list_ = ("list", "数组")

class GroupTypeEnum(StrEnumMore):
    """
    分组码表
    function = ("function", "功能")
    interface = ("interface", "接口")
    """
    menu = ("menu", "菜单")
    permission = ("permission", "权限聚合组")


class PermissionTypeEnum(StrEnumMore):
    """
    权限组预置 code, 目前只有：查看 和 操作
    """
    view = ("view", "查看权限")
    operate = ("operate", "操作权限")


class MenuLevel1(StrEnumMore):
    """
    一级菜单
    """
    index = ("index", "可视化数据")
    monitoring = ("monitoring", "车辆监控")
    analysis = ("analysis", "诊断分析")
    info = ("info", "基础信息")
    config = ("config", "系统配置")
    export = ("export", "数据导出")


class MenuLevel2(StrEnumMore):
    """
    二级菜单
    """
    # 系统首页
    index_ = ("index_", "可视化数据")  # 二级功能
    index_statistic = ("index_statistic", "统计报表")
    # 车辆监控
    monitoring_map = ("monitoring_map", "地图监控")
    monitoring_trace_replay = ("monitoring_trace_replay", "轨迹回放")
    monitoring_truck_station_stat = ("monitoring_truck_station_stat", "有车无站")
    # 诊断分析
    analysis_car_range = ("analysis_car_range", "续航分析")
    analysis_mileage_query = ("analysis_mileage_query", "里程查询")
    analysis_research_dtc = ("analysis_research_dtc", "研发DTC")
    analysis_service_dtc = ("analysis_service_dtc", "服务DTC")
    analysis_reduction_of_amount = ("analysis_reduction_of_amount", "核减分析")
    analysis_under_voltage = ("analysis_under_voltage", "欠压分析")
    analysis_over_temperature = ("analysis_over_temperature", "过温分析")
    # 基础信息
    info_sale = ("info_sale", "销售信息")
    info_product = ("info_product", "产品信息")
    info_customer = ("info_customer", "客户信息")
    info_station_service = ("info_station_service", "站务档案")
    info_region = ("info_region", "区域信息")
    info_dms = ("info_dms", "DMS信息")
    info_400 = ("info_400", "400信息")
    info_research_dtc = ("info_research_dtc", "研发DTC档案")
    info_service_dtc = ("info_service_dtc", "服务DTC档案")
    # 系统配置
    config_role_permission = ("config_role_permission", "角色权限")
    config_forward = ("config_forward", "转发管理")
    config_fleet = ("config_fleet", "车队管理")
    config_can_data = ("config_can_data", "CAN数据管理")
    config_customize_bi = ("config_customize_bi", "报表工厂")
    # 数据导出
    export_can_data = ("export_can_data", "CAN数据")

    export_info_sale = ("export_info_sale", "销售信息")
    export_info_product = ("export_info_product", "产品信息")
    export_info_customer = ("export_info_customer", "客户信息")
    export_info_station_service = ("export_info_station_service", "站务档案")
    export_info_region = ("export_info_region", "区域信息")
    export_info_dms = ("export_info_dms", "DMS信息")
    export_info_400 = ("export_info_400", "400信息")
    export_info_research_dtc = ("export_info_research_dtc", "研发DTC档案")
    export_info_service_dtc = ("export_info_service_dtc", "服务DTC档案")
    export_info_fleet = ("export_info_fleet", "车队信息")

    export_analysis_car_range = ("export_analysis_car_range", "续航分析")
    export_analysis_mileage_query = ("export_analysis_mileage_query", "里程查询")
    export_analysis_research_dtc = ("export_analysis_research_dtc", "研发DTC")
    export_analysis_service_dtc = ("export_analysis_service_dtc", "服务DTC")
    export_analysis_reduction_of_amount = ("export_analysis_reduction_of_amount", "核减分析")
    export_analysis_under_voltage = ("export_analysis_under_voltage", "欠压分析")
    export_analysis_over_temperature = ("export_analysis_over_temperature", "过温分析")


class PermissionEnum(StrEnumMore):
    """
    自定义权限码表, 集成自 MenuLevel2, 将二级菜单映射成权限
    所有的权限判断都使用 apps.permissions.py 中的权限类
    所有权限为:  PermissionTypeEnum + MenuLevel2 + PermissionEnum
    """
    pass


class RoleCodeEnum(StrEnumMore):
    """
    预置角色码表
    """
    super_admin = ("super_admin", "超管")


class ProductLinesEnum(StrEnumMore):
    """
    产品系分类
    """
    i3 = ('i3', 'i3')
    i5 = ('i5', 'i5')
    i6 = ('i6', 'i6')
    pickup = ('pickup', '皮卡')


class DepartmentEnum(StrEnumMore):
    """
    部门码表
    """
    new_energy_service = ("new_energy_service", "新能源服务部")
    new_energy_sale = ("new_energy_sale", "新能源营销大厅")
    new_energy_research = ("new_energy_research", "新能源研究所")


class GenderEnum(StrEnumMore):
    """
    性别码表
    """
    male = ("male", "男")
    female = ("female", "女")


class ExportRecordTypeEnum(StrEnumMore):
    """
    导出记录类型
    """
    market = ("market", "销售信息")
    customer = ("customer", "客户信息")
    product = ("product", "产品信息")
    stationservicearchive = ("stationservicearchive", "站务档案")
    area = ("area", "区域消息")


class IsCompleteEnum(StrEnumMore):
    """
    下载状态
    """
    happening = ("happening", "进行中")
    success = ("success", "成功")
    fail = ("fail", "失败")


class OriginEnum(StrEnumMore):
    """
    更新来源
    """
    dms = ("dms", "服务DMS")
    work_order_400 = ("work_order_400", "400工单")
    typing = ("typing", "手工录入")


class ReducerEnum(StrEnumMore):
    """
    减速器类型
    """
    have = ("have", "有")
    no_have = ("no_have", "无")


class LowPlatformEnum(StrEnumMore):
    """
    低压平台
    """
    voltage_12 = ("voltage_12", "12")
    voltage_24 = ("voltage_24", "24")


class VoltageSwitchEnum(StrEnumMore):
    """
    电压总开关类型
    """
    have = ("have", "有")
    no_have = ("no_have", "无")


class CellTypeEnum(StrEnumMore):
    """
    电芯类型
    """
    lithium_iron = ("lithium_iron", "铁锂")
    ternary = ("ternary", "三元")
    solidity = ("solidity", "固态")


class CoolingMethodEnum(StrEnumMore):
    """
    冷却方式
    """
    natural_cooling = ("natural_cooling", "自然冷却")
    wind = ("wind", "风冷")
    liquid_cooled = ("liquid_cooled", "液冷")
    coolant = ("coolant", "冷媒")


class AirtightInspectionPortEnum(StrEnumMore):
    """
    气密检查口
    """
    have = ("have", "有")
    no_have = ("no_have", "无")


class BoardStorageEnum(StrEnumMore):
    """
    主板存放位置
    """
    individually = ("individually", "单独存放")
    hyperpiesia = ("hyperpiesia", "高压接线盒内")
    box = ("box", "电池箱内")
    other = ("other", "其他")


class VehicleTerminalTypeEnum(StrEnumMore):
    """
    车载终端类型
    """
    single = ("single", "单链路")
    twins = ("twins", "双链路")


class TruckStatusEnum(StrEnumMore):
    """
    车辆状态
    """
    off_line = ("off_line", "离线")
    online = ("online", "在线")
    online_day = ("online_day", "日在线")
    online_week = ("online_week", "周在线")
    online_month = ("online_month", "月在线")


class FaultStatusEnum(StrEnumMore):
    """
    车辆故障状态
    """
    not_fault_code = ("not_fault_code", "无故障码")
    research_fault_code = ("research_fault_code", "研发故障码")
    service_fault_code = ("service_fault_code", "服务故障码")


class ChargeStatusEnum(StrEnumMore):
    """
    车辆充电状态
    """
    charged = ("charged", "充电中")
    discharging = ("discharging", "未充电")
    charged_discharging = ("charged_discharging", "充电 放电")


class StatusEnum(StrEnumMore):
    """
    车队状态
    """
    enable = ("enable", "启用")
    disable = ("disable", "停用")


class ForwardDataEnum(StrEnumMore):
    """
    转发数据类型
    """
    gb = ("gb", "国标数据")
    customize = ("customize", "自定义数据")


class TemperatureStatusEnum(StrEnumMore):
    """
    过温状态
    """
    occur = ("occur", "发生中")
    remove = ("remove", "以消除")


class TemperatureLevelEnum(StrEnumMore):
    """
    过温级别
    """
    a = ("a", "A级")
    b = ("b", "B级")


class PushStatusEnum(StrEnumMore):
    """
    推送状态
    """
    push = ("push", "已推送")
    un_push = ("un_push", "未推送")


# ==================================================
# 在该行上面新增 Enum 类
# ==================================================
# [("name", Enum)]
__enum_set__ = list(filter(
    lambda cls_name_and_cls:
    True if issubclass(cls_name_and_cls[1], (StrEnumMore, IntEnumMore))
            and cls_name_and_cls[1] not in [StrEnumMore, IntEnumMore]
    else False,
    inspect.getmembers(sys.modules[__name__], inspect.isclass)
))

__enum_choices__ = list(
    map(
        lambda cls_name_and_cls:
        (cls_name_and_cls[0], cls_name_and_cls[1].__doc__.strip()),
        __enum_set__
    )
)


def get_enum_content(enum_name: str = None, is_reversed: bool = False):
    enum_content = {}
    enum_list = []  # type: List[Tuple[str, MyEnum]]
    if enum_name:
        try:
            enum_cls = getattr(sys.modules[__name__], enum_name)
            enum_list.append((enum_name, enum_cls))
        except (AttributeError, NotImplementedError):
            pass
    else:
        enum_list = __enum_set__

    for name, cls in enum_list:
        # if format_ == EnumInfoResponseFormats.list_.value:
        #     enum_content[name] = cls.choices()
        # else:
        if is_reversed:
            enum_content[name] = {v: k for k, v in cls.dict()}
        else:
            enum_content[name] = cls.dict()

    return enum_content
