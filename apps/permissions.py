import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


class AccountPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm('account.view_profile')
