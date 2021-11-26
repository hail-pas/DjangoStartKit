import logging

from rest_framework.permissions import BasePermission

from apps.enums import RoleCodeEnum, PermissionEnum
from apps.account.models import Profile

logger = logging.getLogger(__name__)


def _has_permission(request, permission: PermissionEnum) -> bool:
    try:
        profile = request.user.profile  # type: Profile
    except Exception as e:
        logger.warning(e)
        return False
    if RoleCodeEnum.super_admin.value in profile.roles.values_list('code').all():
        return True
    return profile.user.has_perm(f'account.{permission.value}')


class SuperAdminPermission(BasePermission):
    """
    超管账号
    """

    def has_permission(self, request, view):
        try:
            profile = request.user.profile  # type: Profile
        except Exception as e:
            logger.warning(e)
            return False
        if RoleCodeEnum.super_admin.value in profile.roles.values_list('code').all():
            return True
        return False


class ExportTruckStaticDataPermission(BasePermission):
    """
    车辆静态数据导出
    """

    def has_permission(self, request, view):
        return _has_permission(request, PermissionEnum.export_truck_static_data)
