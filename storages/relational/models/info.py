from django.db import models

from storages.relational.base import BaseModel


class Config(BaseModel):
    """
    在线配置
    """

    key = models.CharField(max_length=48, help_text="配置key", verbose_name="key", unique=True)
    value = models.JSONField(help_text="配置内容", verbose_name="value")

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "在线配置"
        verbose_name_plural = verbose_name
