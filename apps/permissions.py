from rest_framework import permissions

logger = logging.getLogger(__name__)


class SuperAdminPermission(permissions.BasePermission):
    """
    Global permission check for blacklisted IPs.
    """

    def has_permission(self, request, view):
        try:
            profile = request.user.profile
        except Exception as e:
            logger.exception(e)
            return False
        if profile.role.code == 'super_admin':
            return True
        return False
