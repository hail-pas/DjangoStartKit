from django.conf import settings
from cachetools.func import ttl_cache
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class CustomModelBackend(ModelBackend):
    """
    自定义获取组权限
    """

    @ttl_cache
    def get_user_related_permissions(self, user_obj_id):  # noqa
        return Permission.objects.filter(
            Q(systemresource__roles__profiles__id=user_obj_id) | Q(profile__id=user_obj_id)
        )

    def _get_group_permissions(self, user_obj):
        # user_groups_field = UserModel._meta.get_field('groups')  # noqa
        # user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        # group_perms = Permission.objects.filter(**{user_groups_query: user_obj})
        # 通过获取角色拥有的系统资源关联的权限
        if user_obj.is_superuser:
            return Permission.objects.all()
        return self.get_user_related_permissions(user_obj.id)

    def has_api_perm(self, user_obj, request, view):  # noqa
        if user_obj.is_active and user_obj.is_superuser:
            return True

        module_name = view.__module__
        class_name = view.__class__.__name__
        action = getattr(view, "action", request.method.lower())

        if (
            module_name in settings.URI_PERMISSION_AUTHENTICATE_EXEMPT["modules"]
            or class_name in settings.URI_PERMISSION_AUTHENTICATE_EXEMPT["classes"]
            or action in settings.URI_PERMISSION_AUTHENTICATE_EXEMPT["actions"]
        ):
            return True

        return (
            user_obj.is_active
            and self.get_user_related_permissions(user_obj.id)
            .filter(codename=f"{module_name}.{class_name}.{action}",)
            .exists()
        )
