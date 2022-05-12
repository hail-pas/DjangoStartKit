# Register your models here.
# Register your models here.
from django.apps import apps
from django.contrib import admin
from django.db.models import fields
from django.contrib.admin.sites import AlreadyRegistered

from conf.config import local_configs

admin.site.site_title = admin.site.site_header = local_configs.PROJECT_NAME + local_configs.ENVIRONMENT
admin.site.index_title = "后台管理"


def get_all_models():
    all_models = set()
    for app_name, model_dict in apps.all_models.items():
        # 可以过滤指定app
        for name, model in model_dict.items():
            all_models.add(model)
    return all_models


app_models = get_all_models()
for model in app_models:  # noqa
    if getattr(model, "hidden_in_admin", False) is True:
        continue
    ffm = model._meta._forward_fields_map.copy()
    list_filter = []
    search_fields = []
    list_display = ["pk"]
    readonly_fields = []
    if ffm.pop("create_time", None):
        readonly_fields.append("create_time")
    if ffm.pop("update_time", None):
        readonly_fields.append("update_time")

    for field_name, field in ffm.items():
        if any((isinstance(field, fields.TextField), isinstance(field, fields.CharField),)):
            search_fields.append(field_name)

        elif isinstance(field, fields.BooleanField):
            list_filter.append(field_name)

        elif isinstance(field, fields.related.ForeignKey):
            if not field_name.endswith("_id"):
                list_filter.append(field_name)
        elif any(
            (
                isinstance(field, fields.related.ManyToManyField),
                isinstance(field, fields.related.ForeignKey),
                isinstance(field, fields.files.FileField),
                isinstance(field, fields.URLField),
                isinstance(field, fields.TextField),
                # isinstance(field, models.JSONField),
                field_name == "id",
            )
        ):
            continue
        list_display.append(field_name)

    if len(list_display) > 15:
        list_display = list_display[:15]
    if len(list_filter) > 8:
        list_filter = list_filter[:8]
    for one in ["ordering", "is_hidden", "deleted"]:
        if one in list_display:
            list_display.remove(one)
            # list_display.append(one)

    class XXXAdmin(admin.ModelAdmin):  # noqa
        list_filter = list_filter
        list_display = list_display
        search_fields = search_fields
        readonly_fields = readonly_fields

    try:  # noqa
        admin.site.register(model, XXXAdmin)
    except AlreadyRegistered:
        pass
