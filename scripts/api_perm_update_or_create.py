from scripts import django_setup  # noqa
from common.django.paths import API_DICT
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.account.models import SystemResource

if __name__ == '__main__':
    """
    创建或更新 API Permissions
    """
    content_type = ContentType.objects.filter(app_label=SystemResource._meta.app_label,
                                              model=SystemResource._meta.model_name).first()
    if not content_type:
        raise RuntimeError("未定义系统资源对象")
    for codename, name in API_DICT.items():
        perms = Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={
                "name": name
            }
        )
    print("Success")

