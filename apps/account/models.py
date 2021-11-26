# Create your models here.
from datetime import datetime
from typing import List

from django.db import models
from django.contrib.auth.models import Group, User
from storages.mysql import BaseModel
from apps import enums


class CustomizeGroup(Group):
    parent_node = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        verbose_name="父节点",
        blank=True,
        null=True,
        default=None,
        help_text='父节点的ID',
    )
    group_type = models.CharField(
        '组类型',
        max_length=16,
        choices=enums.GroupTypeEnum.choices(),
        blank=False,
        null=False,
        default=enums.GroupTypeEnum.menu_level1.value,
        help_text='组类型',
    )
    code = models.CharField(
        '标识编码',
        max_length=32,
        help_text='标识编码',
    )
    order_num = models.IntegerField(
        '排列序号',
        default=1,
        help_text='排列序号',
    )
    enabled = models.BooleanField(
        "启用状态",
        default=True,
        help_text="当前分组是否可用"
    )

    class Meta:
        verbose_name = u'自定义分组'
        verbose_name_plural = verbose_name
        permissions = enums.PermissionEnum.choices()


class Role(BaseModel):
    code = models.CharField(
        '英文Code',
        max_length=64,
        help_text='英文Code',
    )
    name = models.CharField(
        '名称',
        max_length=64,
        unique=True,
        help_text=u'角色名称',
    )
    groups = models.ManyToManyField(
        CustomizeGroup,
        verbose_name='角色分组',
        help_text='角色分组',
    )
    remark = models.CharField(
        '备注',
        max_length=128,
        blank=True,
        default="",
        help_text='角色说明',
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = verbose_name


class Profile(BaseModel):
    roles = models.ManyToManyField(
        Role,
        verbose_name='所属角色',
        help_text=u'所属角色(int)',
    )
    user = models.OneToOneField(
        User,
        verbose_name='内置用户',
        on_delete=models.CASCADE,
        help_text=u'用户(int)',
    )
    name = models.CharField(
        '名字',
        max_length=64,
        blank=True,
        default='',
        help_text='姓名',
    )
    phone = models.CharField(
        u'电话',
        max_length=11,
        unique=True,
        help_text=u'电话',
    )

    @property
    def menu_level1_groups(self):
        g_ids = self.user.groups.values_list('id').all()
        return CustomizeGroup.objects.filter(
            id__in=g_ids, group_type=enums.GroupTypeEnum.menu_level1.value, enabled=True).all()

    @property
    def menu_level2_groups(self):
        g_ids = self.user.groups.values_list('id').all()
        return CustomizeGroup.objects.filter(
            id__in=g_ids, group_type=enums.GroupTypeEnum.menu_level2.value, enabled=True).all()

    @property
    def permissions_groups(self):
        g_ids = self.user.groups.values_list('id').all()
        return CustomizeGroup.objects.filter(
            id__in=g_ids, group_type=enums.GroupTypeEnum.permissions.value, enabled=True).all()

    @property
    def role_codes(self):
        return self.roles.values_list("code").all()

    @property
    def role_names(self):
        return self.roles.values_list("name").all()

    @property
    def last_login_time(self) -> datetime:
        return self.user.last_login

    @property
    def is_active(self):
        return self.user.is_active
