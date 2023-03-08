from typing import List
from contextlib import contextmanager

from django.db import models, transaction
from django.utils import timezone
from django.db.models import Manager
from polymorphic.managers import PolymorphicManager
from django.db.transaction import get_connection
from django.db.models.fields.files import FieldFile

from storages import enums


@contextmanager
def lock_table(model):
    with transaction.atomic():
        cursor = get_connection().cursor()
        cursor.execute(f"LOCK TABLE {model._meta.db_table} WRITE")  # noqa
        try:
            yield
        finally:
            cursor.execute("UNLOCK TABLES;")
            cursor.close()


@contextmanager
def suppress_auto_now(model, field_names=None):
    """
    Temp disable auto_now and auto_now_add for django fields
    @model - model class or instance
    @field_names - list of field names to suppress or all model's
                   fields that support auto_now_add, auto_now"""

    def get_auto_now_fields(user_selected_fields):
        for field in model._meta.get_fields():
            field_name = field.name
            if user_selected_fields and field_name not in user_selected_fields:
                continue
            if hasattr(field, "auto_now") or hasattr(field, "auto_now_add"):
                yield field

    fields_state = {}

    for field in get_auto_now_fields(user_selected_fields=field_names):
        fields_state[field] = {"auto_now": field.auto_now, "auto_now_add": field.auto_now_add}

    for field in fields_state:
        field.auto_now = False
        field.auto_now_add = False
    try:
        yield
    finally:
        for field, state in fields_state.items():
            field.auto_now = state["auto_now"]
            field.auto_now_add = state["auto_now_add"]


class SoftDeletedManager(Manager):
    """
    deleted 软删除
    """

    def filter_deleted_false(self, *args, **kwargs):
        defaults = {"delete_time__isnull": True}
        defaults.update(kwargs)
        return self.get_queryset().filter(*args, **defaults)


class BaseModel(models.Model):
    objects = SoftDeletedManager()

    create_time = models.DateTimeField("创建时间", auto_now_add=True, help_text="创建时间", editable=False)
    update_time = models.DateTimeField("更新时间", auto_now=True, help_text="更新时间", editable=False)
    delete_time = models.DateTimeField("删除时间", default=lambda : timezone.datetime.min, editable=False, help_text="删除时间, 与其他字段联合唯一; 不能为null, 会导致唯一约束失效")
    # delete_status = models.BooleanField("是否已删除", default=False, help_text="是否已删除")
    # delete_id = models.BigIntegerField("删除ID", default=0, help_text="默认为0, 删除的情况下为记录主键; 与其他字段联合唯一; 用于更高并发的场景")

    def save(self, *args, **kwargs):
        """ On save, update timestamps """
        self.update_time = timezone.now()
        update_fields = kwargs.get("update_fields", None)  # type: List
        if update_fields:
            kwargs["update_fields"] = set(update_fields + ["update_time"])
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["-id"]  # 默认倒序


class PolySoftDeletedManager(PolymorphicManager):
    def filter_deleted_false(self, *args, **kwargs):
        defaults = {"delete_time__isnull": True}
        defaults.update(kwargs)
        return self.get_queryset().filter(*args, **defaults)


class PolyBaseModel(BaseModel):
    objects = PolySoftDeletedManager()

    class Meta:
        abstract = True
        ordering = ["-id"]  # 默认倒序


class LabelFieldMixin(models.Model):
    label = models.CharField(verbose_name="名称", max_length=32, help_text="名称")

    def __str__(self):
        return self.label

    class Meta:
        abstract = True


class RemarkFieldMixin(models.Model):
    remark = models.CharField("备注", max_length=128, blank=True, default="", help_text="备注说明")

    class Meta:
        abstract = True


class OrderWeightFieldMixin(models.Model):
    order_weight = models.CharField(max_length=16, verbose_name="排序比重", help_text="排序比重，越大越前", default="0")

    class Meta:
        abstract = True


class StatusFieldMixin(models.Model):
    status = models.CharField(
        "状态", max_length=16, choices=enums.Status.choices, default=enums.Status.enable.value, help_text="状态"
    )

    class Meta:
        abstract = True


file_field = models.FileField(verbose_name="文件路径", blank=True, max_length=255)


class FileLinksPropertyMixin:
    @property
    def file_links(self):
        files = []
        for file in self.files.all():  # noqa
            file["path"] = FieldFile(instance=self, field=file_field, name=file.path)
            files.append(file)
        return files
