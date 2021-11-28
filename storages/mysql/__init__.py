from typing import List

from django.db import models
from django.utils import timezone
from django.db.models.manager import Manager


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
