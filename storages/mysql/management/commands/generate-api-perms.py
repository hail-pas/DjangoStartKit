from django.core.management import BaseCommand


class Command(BaseCommand):
    help = """生成或更新 API 接口权限"""

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        from common.django.paths import API_DICT
        from storages.mysql.models import SystemResource

        content_type = ContentType.objects.filter(
            app_label=SystemResource._meta.app_label, model=SystemResource._meta.model_name
        ).first()
        if not content_type:
            raise RuntimeError("未定义系统资源对象")
        for codename, name in API_DICT.items():
            print("%50s %s" % (codename, name))
            perms, created = Permission.objects.update_or_create(
                content_type=content_type, codename=codename, defaults={"name": name}
            )
        print("Success")
