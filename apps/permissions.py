import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps import enums
from apps.account.models import Profile, CustomizeGroup
from common.types import StrEnumMore
from common.utils import flatten_list

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

    def has_pre_permission(self, request, permission: StrEnumMore):
        profile = request.user  # type: Profile
        if profile.is_anonymous:
            raise PermissionDenied("权限不足")
        if enums.RoleCodeEnum.super_admin.value in profile.roles.values_list('code', flat=True).all():
            return True
        menu_level2 = CustomizeGroup.objects.filter(code=permission.value).first()
        if not menu_level2:
            # TODO: 非菜单权限
            return False
        if menu_level2.id in flatten_list(profile.roles.values_list('view_groups', flat=True).all()):
            return True
        return False


class PrerequisiteOperatePermission(BasePermission):
    """
    先决条件 操作权限
    """

    def has_pre_permission(self, request, permission: StrEnumMore):
        profile = request.user  # type: Profile
        if profile.is_anonymous:
            raise PermissionDenied("权限不足")
        if enums.RoleCodeEnum.super_admin.value in profile.roles.values_list('code', flat=True).all():
            return True
        menu_level2 = CustomizeGroup.objects.filter(code=permission.value).first()
        if not menu_level2:
            # TODO: 非菜单权限
            return False
        if menu_level2.id in flatten_list(profile.roles.values_list('operate_groups', flat=True).all()):
            return True
        return False


# >>>>>>>>>> 首页
class IndexPermission:
    class ViewPermission:
        class ViewIndexPermission(PrerequisiteViewPermission):
            """
            查看首页权限
            """

            def has_permission(self, request, view):
                return self.has_pre_permission(request, enums.MenuLevel2.index_) and _has_permission(request,
                                                                                                     enums.MenuLevel2.index_)

    class OperatePermission:
        class OperateInfoSalePermission(PrerequisiteOperatePermission):
            """
            操作首页权限
            """

            def has_permission(self, request, view):
                return self.has_pre_permission(request, enums.MenuLevel2.index_) and _has_permission(request,
                                                                                                        enums.MenuLevel2.index_)