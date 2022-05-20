from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class CustomModelBackend(ModelBackend):
    """
    自定义获取组权限
    """

    def get_user_related_permissions(self, user_obj):  # noqa
        return user_obj.roles.all().values_list("system_resources__permissions__id", flat=True)

    def _get_user_permissions(self, user_obj):
        return user_obj.user_permissions.all()

    def _get_group_permissions(self, user_obj):
        # user_groups_field = UserModel._meta.get_field('groups')  # noqa
        # user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        # group_perms = Permission.objects.filter(**{user_groups_query: user_obj})
        # 通过获取角色拥有的系统资源关联的权限
        if user_obj.is_superuser:
            return Permission.objects.all()
        system_resource_perms = Permission.objects.filter(id__in=self.get_user_related_permissions(user_obj))
        return system_resource_perms

    def has_api_perm(self, user_obj, method, uri):  # noqa
        if user_obj.is_active and user_obj.is_superuser:
            return True
        return user_obj.is_active and Permission.objects.filter(
            id__in=self.get_user_related_permissions(user_obj), codename=f"{method.upper()}:{uri}"
        )
