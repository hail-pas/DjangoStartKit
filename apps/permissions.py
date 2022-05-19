import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


class URIBasedPermission(BasePermission):
    def has_permission(self, request, view):
        # TODO: 基于接口URI的权限校验
        return request.user.has_perm("account.view_profile")
