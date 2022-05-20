import re
import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


class URIBasedPermission(BasePermission):
    def has_permission(self, request, view):
        path_info = re.sub(r"/([\d+])/", "/{id}/", request.path_info, count=1)
        return bool(request.user and request.user.is_authenticated) and (
            request.user.has_perm("account.view_profile") or request.user.has_api_perm(request.method, path_info)
        )
