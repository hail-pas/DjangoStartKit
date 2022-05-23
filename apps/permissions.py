import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


class URIBasedPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) and request.user.has_api_perm(request, view)
