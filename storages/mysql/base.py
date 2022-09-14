from typing import List
from contextlib import contextmanager

from django.db import models, transaction
from django.utils import timezone
from django.db.models import Manager
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


class DeletedFieldManager(Manager):
    """
    deleted 软删除
    """

    def get_queryset(self):
        return super().get_queryset().filter(delete_time__isnull=True)


class BaseModel(models.Model):
    objects = Manager()

    create_time = models.DateTimeField("创建时间", auto_now_add=True, help_text="创建时间", editable=False)
    update_time = models.DateTimeField("更新时间", auto_now=True, help_text="更新时间", editable=False)
    delete_time = models.DateTimeField("删除时间", null=True, blank=True, editable=False, help_text="删除时间")

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
        "状态", max_length=16, choices=enums.Status.choices(), default=enums.Status.enable.value, help_text="状态"
    )

    class Meta:
        abstract = True


file_field = models.FileField(verbose_name="文件路径", blank=True, max_length=255)


class FileLinksPropertyMixin:
    @property
    def file_links(self):
        return [
            FieldFile(instance=self, field=file_field, name=path)
            for path in flatten_list(self.pictures.all().values_list("path"))  # noqa
        ]
