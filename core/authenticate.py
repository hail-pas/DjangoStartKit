from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class CustomModelBackend(ModelBackend):
    """
    自定义获取组权限
    """

    def _get_user_permissions(self, user_obj):
        return user_obj.user_permissions.all()

    def _get_group_permissions(self, user_obj):
        # user_groups_field = UserModel._meta.get_field('groups')  # noqa
        # user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        # group_perms = Permission.objects.filter(**{user_groups_query: user_obj})
        # 通过获取角色拥有的系统资源关联的权限
        system_resource_perm_ids = user_obj.roles.all().values_list("system_resources__permissions__id", flat=True)
        system_resource_perms = Permission.objects.filter(id__in=system_resource_perm_ids)
        return system_resource_perms
