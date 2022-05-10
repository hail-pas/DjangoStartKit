from typing import List

from django.db import models
from django.utils import timezone
from django.db.models.manager import Manager


class DeletedFieldManager(Manager):
    """
    deleted 软删除
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


class BaseModel(models.Model):
    objects = Manager()

    create_time = models.DateTimeField(
        "创建时间",
        auto_now_add=True,
        help_text="创建时间",
        editable=False
    )
    update_time = models.DateTimeField(
        u"更新时间",
        auto_now=True,
        help_text="更新时间",
    )
    deleted = models.BooleanField(
        u"是否已删除",
        default=False,
        blank=False,
        help_text="是否已删除",
    )

    def save(self, *args, **kwargs):
        """ On save, update timestamps """
        self.update_time = timezone.now()
        update_fields = kwargs.get("update_fields", None)  # type: List
        if update_fields:
            kwargs["update_fields"] = set(update_fields + ["update_time"])
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ['-id']  # 默认倒序


class LabelFieldMixin(models.Model):
    label = models.CharField(
        verbose_name="名称",
        max_length=32,
        help_text="名称"
    )

    def __str__(self):
        return self.label

    class Meta:
        abstract = True


class RemarkFieldMixin(models.Model):
    remark = models.CharField(
        '备注',
        max_length=128,
        blank=True,
        default="",
        help_text='备注说明',
    )

    class Meta:
        abstract = True
