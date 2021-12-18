import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps import enums
from apps.account.models import Profile
from common.types import StrEnumMore

logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


def _has_permission(request, permission: StrEnumMore) -> bool:
    profile = request.user  # type: Profile
    if profile.is_anonymous:
        raise PermissionDenied("权限不足")
    if enums.RoleCodeEnum.super_admin.value in profile.roles.values_list('code', flat=True).all():
        return True
    return profile.has_perm(f'account.{permission.value}')


class SuperAdminPermission(BasePermission):
    """
    超管账号
    """

    def has_permission(self, request, view):
        profile = request.user  # type: Profile
        if profile.is_anonymous:
            raise PermissionDenied("权限不足")
        if enums.RoleCodeEnum.super_admin.value in profile.roles.values_list('code', flat=True).all():
            return True
        return False


class PrerequisiteViewPermission(BasePermission):
    """
    先决条件 查看权限
    """

    def has_permission(self, request, view):
        return _has_permission(request, enums.PermissionTypeEnum.view)


class PrerequisiteOperatePermission(BasePermission):
    """
    先决条件 查看权限
    """

    def has_permission(self, request, view):
        return _has_permission(request, enums.PermissionTypeEnum.operate)


# >>>>>>>>>> 首页
class IndexPermission:
    class ViewPermission:
        class ViewIndexPermission(PrerequisiteViewPermission):
            """
            查看首页权限
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.index_)


# >>>>>>>>>> 车辆监控
class MonitoringPermission:
    class ViewPermission:
        class ViewMonitoringMapPermission(PrerequisiteViewPermission):
            """
            查看地图监控权限
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.monitoring_map)

        class ViewMonitoringTraceReplayPermission(PrerequisiteViewPermission):
            """
            查看轨迹回放
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.monitoring_trace_replay)

        class ViewMonitoringTruckStationStatPermission(PrerequisiteViewPermission):
            """
            查看有车无站
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.monitoring_truck_station_stat)


# >>>>>>>>>> 诊断分析
class AnalysisPermission:
    class ViewPermission:
        class ViewAnalysisCarRangePermission(PrerequisiteViewPermission):
            """
            查看续航分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_car_range)

        class ViewAnalysisMileageQueryPermission(PrerequisiteViewPermission):
            """
            查看里程查询
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_mileage_query)

        class ViewAnalysisResearchDTCPermission(PrerequisiteViewPermission):
            """
            查看研发DTC分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_research_dtc)

        class ViewAnalysisServiceDTCPermission(PrerequisiteViewPermission):
            """
            查看服务DTC分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_service_dtc)

        class ViewAnalysisReductionOfAmountPermission(PrerequisiteViewPermission):
            """
            查看核减分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_reduction_of_amount)

        class ViewAnalysisUnderVoltagePermission(PrerequisiteViewPermission):
            """
            查看欠压分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_under_voltage)

        class ViewAnalysisOverTemperaturePermission(PrerequisiteViewPermission):
            """
            查看过温分析
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.analysis_over_temperature)


# >>>>>>>>>> 基础信息
class InfoPermission:
    class ViewPermission:
        class ViewInfoSalePermission(PrerequisiteViewPermission):
            """
            查看销售信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_sale)

        class ViewInfoProductPermission(PrerequisiteViewPermission):
            """
            查看产品信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_product)

        class ViewInfoCustomerPermission(PrerequisiteViewPermission):
            """
            查看客户信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_customer)

        class ViewInfoStationServicePermission(PrerequisiteViewPermission):
            """
            查看站务档案信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_station_service)

        class ViewInfoRegionPermission(PrerequisiteViewPermission):
            """
            查看区域信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_region)

        class ViewInfoDMSPermission(PrerequisiteViewPermission):
            """
            查看DMS信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_dms)

        class ViewInfo400Permission(PrerequisiteViewPermission):
            """
            查看400信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_400)

        class ViewInfoResearchDTCPermission(PrerequisiteViewPermission):
            """
            查看研发DTC档案
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_research_dtc)

        class ViewInfoServiceDTCPermission(PrerequisiteViewPermission):
            """
            查看服务DTC档案
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_service_dtc)

    class OperatePermission:
        class OperateInfoSalePermission(PrerequisiteOperatePermission):
            """
            操作销售信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_sale)

        class OperateInfoProductPermission(PrerequisiteOperatePermission):
            """
            操作产品信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_product)

        class OperateInfoCustomerPermission(PrerequisiteOperatePermission):
            """
            操作客户信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_customer)

        class OperateInfoStationServicePermission(PrerequisiteOperatePermission):
            """
            操作站务档案信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_station_service)

        class OperateInfoRegionPermission(PrerequisiteOperatePermission):
            """
            操作区域信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_region)

        class OperateInfoDMSPermission(PrerequisiteOperatePermission):
            """
            操作DMS信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_dms)

        class OperateInfo400Permission(PrerequisiteOperatePermission):
            """
            操作400信息
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request, enums.MenuLevel2.info_400)

        class OperateInfoResearchDTCPermission(PrerequisiteOperatePermission):
            """
            操作研发DTC档案
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_research_dtc)

        class OperateInfoServiceDTCPermission(PrerequisiteOperatePermission):
            """
            操作服务DTC档案
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.info_service_dtc)


# >>>>>>>>>> 系统配置
class ConfigPermission:
    class ViewPermission:
        class ViewConfigRolePermissionPermission(PrerequisiteViewPermission):
            """
            查看角色权限配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_role_permission)

        class ViewConfigForwardPermission(PrerequisiteViewPermission):
            """
            查看转发配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_forward)

        class ViewConfigFleetPermission(PrerequisiteViewPermission):
            """
            查看车队配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_fleet)

        class ViewConfigCANDataPermission(PrerequisiteViewPermission):
            """
            查看CAN数据管理
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_can_data)

        class ViewConfigCustomizeBIPermission(PrerequisiteViewPermission):
            """
            查看自定义BI配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_customize_bi)

    class OperatePermission:
        class OperateConfigRolePermissionPermission(PrerequisiteOperatePermission):
            """
            操作角色权限配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_role_permission)

        class OperateConfigForwardPermission(PrerequisiteOperatePermission):
            """
            操作转发配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_forward)

        class OperateConfigFleetPermission(PrerequisiteOperatePermission):
            """
            操作车队配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_fleet)

        class OperateConfigCANDataPermission(PrerequisiteOperatePermission):
            """
            操作CAN数据管理
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_can_data)

        class OperateConfigCustomizeBIPermission(PrerequisiteOperatePermission):
            """
            操作自定义BI配置
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.config_customize_bi)


# >>>>>>>>>> 数据导出
class ExportPermission:
    class ViewPermission:
        class ViewExportCANDataPermission(PrerequisiteViewPermission):
            """
            查看CAN数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_can_data)

        class ViewExportInfoSalePermission(PrerequisiteViewPermission):
            """
            查看销售信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_sale)

        class ViewExportInfoProductPermission(PrerequisiteViewPermission):
            """
            查看产品信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_product)

        class ViewExportInfoCustomerPermission(PrerequisiteViewPermission):
            """
            查看客户信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_customer)

        class ViewExportInfoStationServicePermission(PrerequisiteViewPermission):
            """
            查看站务信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_station_service)

        class ViewExportInfoRegionPermission(PrerequisiteViewPermission):
            """
            查看区域信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_region)

        class ViewExportInfoDMSPermission(PrerequisiteViewPermission):
            """
            查看DMS信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_dms)

        class ViewExportInfo400Permission(PrerequisiteViewPermission):
            """
            查看400数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_400)

        class ViewExportInfoResearchDTCPermission(PrerequisiteViewPermission):
            """
            查看研发DTC档案导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_research_dtc)

        class ViewExportInfoServiceDTCPermission(PrerequisiteViewPermission):
            """
            查看服务DTC档案导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_service_dtc)

        class ViewExportInfoFleetPermission(PrerequisiteViewPermission):
            """
            查看车队信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_fleet)

        class ViewExportAnalysisCarRangePermission(PrerequisiteViewPermission):
            """
            查看续航分析导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_car_range)

        class ViewExportAnalysisMileageQueryPermission(PrerequisiteViewPermission):
            """
            查看里程查询导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_mileage_query)

        class ViewExportAnalysisResearchDTCPermission(PrerequisiteViewPermission):
            """
            查看研发DTC分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_research_dtc)

        class ViewExportAnalysisServiceDTCPermission(PrerequisiteViewPermission):
            """
            查看服务DTC分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_service_dtc)

        class ViewExportAnalysisReductionOfAmountPermission(PrerequisiteViewPermission):
            """
            查看核减分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_reduction_of_amount)

        class ViewExportAnalysisUnderVoltagePermission(PrerequisiteViewPermission):
            """
            查看欠压分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_under_voltage)

        class ViewExportAnalysisOverTemperaturePermission(PrerequisiteViewPermission):
            """
            查看过温分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_over_temperature)

    class OperatePermission:
        class OperateExportCANDataPermission(PrerequisiteOperatePermission):
            """
            操作CAN数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_can_data)

        class OperateExportInfoSalePermission(PrerequisiteOperatePermission):
            """
            操作销售信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_sale)

        class OperateExportInfoProductPermission(PrerequisiteOperatePermission):
            """
            操作产品信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_product)

        class OperateExportInfoCustomerPermission(PrerequisiteOperatePermission):
            """
            操作客户信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_customer)

        class OperateExportInfoStationServicePermission(PrerequisiteOperatePermission):
            """
            操作站务信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_station_service)

        class OperateExportInfoRegionPermission(PrerequisiteOperatePermission):
            """
            操作区域信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_region)

        class OperateExportInfoDMSPermission(PrerequisiteOperatePermission):
            """
            操作DMS信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_dms)

        class OperateExportInfo400Permission(PrerequisiteOperatePermission):
            """
            操作400数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_400)

        class OperateExportInfoResearchDTCPermission(PrerequisiteOperatePermission):
            """
            操作研发DTC档案导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_research_dtc)

        class OperateExportInfoServiceDTCPermission(PrerequisiteOperatePermission):
            """
            操作服务DTC档案导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_service_dtc)

        class OperateExportInfoFleetPermission(PrerequisiteOperatePermission):
            """
            操作车队信息导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_info_fleet)

        class OperateExportAnalysisCarRangePermission(PrerequisiteOperatePermission):
            """
            操作续航分析导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_car_range)

        class OperateExportAnalysisMileageQueryPermission(PrerequisiteOperatePermission):
            """
            操作里程查询导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_mileage_query)

        class OperateExportAnalysisResearchDTCPermission(PrerequisiteOperatePermission):
            """
            操作研发DTC分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_research_dtc)

        class OperateExportAnalysisServiceDTCPermission(PrerequisiteOperatePermission):
            """
            操作服务DTC分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_service_dtc)

        class OperateExportAnalysisReductionOfAmountPermission(PrerequisiteOperatePermission):
            """
            操作核减分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_reduction_of_amount)

        class OperateExportAnalysisUnderVoltagePermission(PrerequisiteOperatePermission):
            """
            操作欠压分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_under_voltage)

        class OperateExportAnalysisOverTemperaturePermission(PrerequisiteOperatePermission):
            """
            操作过温分析数据导出
            """

            def has_permission(self, request, view):
                return super().has_permission(request, view) and _has_permission(request,
                                                                                 enums.MenuLevel2.export_analysis_over_temperature)
