from django.db import models

from storages import enums
from storages.relational.base import BaseModel
from storages.relational.models import Profile


class ThirdService(BaseModel):
    label = models.CharField(max_length=32, verbose_name="名称标识", help_text="名称标识")
    identifier = models.CharField(max_length=64, verbose_name="唯一标识", help_text="唯一标识", unique=True)
    api_key = models.CharField(max_length=64, verbose_name="api key", help_text="api key")
    sign_key = models.CharField(max_length=64, verbose_name="sign key", help_text="签名key")
    protocol = models.CharField(choices=enums.Protocol.choices, default=enums.Protocol.http.value, max_length=16)
    host = models.CharField(max_length=255, verbose_name="Host", help_text="Host不带端口")
    port = models.IntegerField(null=True, blank=True, verbose_name="端口", help_text="端口")

    @property
    def address(self):
        addr = f"{self.protocol}://{self.host}"
        if self.port:
            addr += f":{self.port}"
        return addr

    def __str__(self):
        return f"{self.label}:{self.identifier}"

    class Meta:
        verbose_name = "三方服务"
        verbose_name_plural = verbose_name
        ordering = ["id"]


class ReferenceProfile(BaseModel):
    third_service = models.ForeignKey(to=ThirdService, on_delete=models.CASCADE, help_text="关联系统", verbose_name="关联系统")
    profile = models.ForeignKey(to=Profile, on_delete=models.CASCADE, help_text="用户", verbose_name="用户")
    referenced_id = models.CharField(max_length=64, help_text="关联ID", verbose_name="关联ID")

    def __str__(self):
        return f"{self.profile}->{self.third_service}:{self.referenced_id}"

    class Meta:
        verbose_name = "三方服务用户ID关联"
        verbose_name_plural = verbose_name
        unique_together = (("third_service", "profile",),)
