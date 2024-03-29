# Create your models here.
import string

from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.db.models import Manager
from polymorphic.models import PolymorphicModel
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission, GroupManager, _user_has_perm, _user_has_module_perms  # noqa
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.validators import UnicodeUsernameValidator

from storages import enums
from common.utils import flatten_list, file_upload_to
from common.django.perms import _user_has_api_perm  # noqa
from storages.relational.base import BaseModel, PolyBaseModel, LabelFieldMixin, RemarkFieldMixin, PolySoftDeletedManager

from django.contrib.auth.models import _user_get_permissions  # noqa; noqa

allowed_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits  # noqa


class BaseUserManager(Manager):
    @classmethod
    def normalize_email(cls, email):
        """
        Normalize the email address by lowercase the domain part of it.
        """
        email = email or ""
        try:
            email_name, domain_part = email.strip().rsplit("@", 1)
        except ValueError:
            pass
        else:
            email = email_name + "@" + domain_part.lower()
        return email

    def make_random_password(self, length=10, allowed_chars=allowed_chars):  # noqa
        """
        Generate a random password with the given length and given
        allowed_chars. The default value of allowed_chars does not have "I" or
        "O" or letters and digits that look similar -- just to avoid confusion.
        """
        return get_random_string(length, allowed_chars)

    def get_by_natural_key(self, username):
        user = self.filter(**{self.model.USERNAME_FIELD: username}).prefetch_related("roles").first()
        if not user:
            raise self.model.DoesNotExist()
        return user


class ProfileManager(BaseUserManager, PolySoftDeletedManager):
    def create_user(self, username, phone, password, **extra_fields):
        user = self.model(username=username, phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, phone, password, **extra_fields)


class PermissionsMixin(models.Model):
    """
    Add the fields and methods necessary to support the Group and Permission
    models using the ModelBackend.
    """

    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_("Designates that this user has all permissions without " "explicitly assigning them."),
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="profile_set",
        related_query_name="profile",
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has directly.
        Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, "user")

    def get_group_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has through their
        groups. Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, "group")

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "all")

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:  # noqa
            return True

        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Return True if the user has each of the specified permissions. If
        object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:  # noqa
            return True

        return _user_has_module_perms(self, app_label)


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(_("用户名"), max_length=128, help_text="用户名, 最长128",)
    phone = models.CharField(
        "电话", max_length=11, unique=True, help_text="电话", error_messages={"unique": "使用该手机号的用户已存在"}
    )
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"), default=False, help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. " "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["username", "password"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""  # noqa
        send_mail(subject, message, from_email, [self.email], **kwargs)


# ========================================================================
"""
用户 - 角色（资源组） - 资源 （权限组）- 权限（权限互斥、依赖、包含）
系统资源：菜单、按钮、接口； 资源拥有权限； 角色获得其关联系统资源的所有相关权限
    名称
    父级
    标识
    类型（菜单/按钮/接口）
    前端路由
    是否启用
    排序
    备注
数据资源权限：需要权限控制的业务数据
    名称
    ContentType
    # TODO: 具体方案待确定
    可选择权限项（存储到用户的数据权限配置字典, 角色也可以存储数据权限配置字典）
    排序
    备注

# 对象
用户 - 角色 - 系统资源 - 权限 ： 多对多关系
用户 - 权限 ： 多对多关系
系统 ： 可选（用于子系统）
# 对象描述
系统资源类别：菜单、按钮、接口
权限：基于接口粒度控制
用户可拥有多个角色，每个角色拥有多个系统资源，系统资源关联多个权限


"""


class SystemResource(LabelFieldMixin, RemarkFieldMixin, BaseModel):
    """
    系统资源
    """

    parent = models.ForeignKey(
        to="self",
        related_name="children",
        on_delete=models.CASCADE,
        verbose_name="父级",
        help_text="父级",
        blank=True,
        null=True,
    )
    reference_to = models.ForeignKey(
        to="self",
        related_name="reference_from",
        on_delete=models.SET_NULL,
        verbose_name="跳转关联节点",
        help_text="跳转关联节点",
        blank=True,
        null=True,
    )
    code = models.CharField("标识编码", max_length=64, help_text="标识编码，冒号标识层级 {parent}:{current}",)
    route_path = models.CharField("前端路由", max_length=128, help_text="前端路由", null=True, blank=True)
    icon_path = models.CharField("图标", max_length=128, help_text="图标", null=True, blank=True)
    type = models.CharField("资源类型", max_length=16, choices=enums.SystemResourceTypeEnum.choices(), help_text="组类型",)
    order_num = models.IntegerField("排列序号", default=1, help_text="排列序号",)
    enabled = models.BooleanField("启用状态", default=True, help_text="当前分组是否可用")
    assignable = models.BooleanField("是否可配置", default=True, help_text="配置时是否可分配")
    permissions = models.ManyToManyField(Permission, verbose_name="权限", help_text="权限", blank=True)

    @classmethod
    def root_menus(cls, profile):
        menus = cls.objects.filter(
            parent=None, enabled=True, type=enums.SystemResourceTypeEnum.menu.value, systems__in=profile.systems.all()
        )
        return menus

    def __str__(self):
        return f"{self.parent.label + '-' if self.parent else ''}" + self.label

    class Meta:
        verbose_name = "系统资源"
        verbose_name_plural = verbose_name
        permissions = enums.PermissionEnum.choices()
        unique_together = ("code", "parent")
        ordering = ["order_num"]


# class DataFilter(RemarkFieldMixin, BaseModel):
#     label = models.CharField(verbose_name="名称", max_length=32, help_text="名称", unique=True)
#     content_type = models.ForeignKey(
#         to=ContentType, on_delete=models.CASCADE, related_name="data_filters", verbose_name="数据模型", help_text="数据模型",
#     )
#     eval_string = models.CharField(max_length=256, null=True, blank=True, verbose_name="代码字符串", help_text="代码字符串, 为Q查询")
#     """
#     eval_string_prototype = "Q({field1}) & Q({field2}) | Q({field3})"
#     eval_string = eval_string_prototype.format(**{"field1": value1, })
#     """
#     eval_string_prototype = models.CharField(max_length=512, verbose_name="代码字符串模版", help_text="代码字符串模版")
#     field = models.JSONField("选中过滤字段项", default=list, blank=True, help_text="选中过滤字段项")
#     """
#     [
#         [ # field1
#             ["label", "value1"],
#             ["label", "value2"],
#         ],
#         [ # field2
#             [],
#             [],
#         ],
#     ]
#     """
#     options = models.JSONField(
#         max_length=256, default=list, blank=True, verbose_name="选中的代码字符串", help_text="代码字符串, 一般为字典filter"
#     )
#
#     def __str__(self):
#         return self.label
#
#     class Meta:
#         app_label = "account"
#         verbose_name = "数据过滤Q配置"
#         verbose_name_plural = verbose_name
#         ordering = ["-id"]


# class DataFilterFields(LabelFieldMixin, RemarkFieldMixin, BaseModel):
#     content_type = models.ForeignKey(
#         to=ContentType, on_delete=models.CASCADE, related_name="data_sources", verbose_name="数据模型", help_text="数据模型"
#     )
#     fields = models.JSONField("过滤字段项", default=list, blank=True, help_text="过滤字段项")
#     """
#         [
#             [ # field1
#                 ["label", "value1"],
#                 ["label", "value2"],
#             ],
#             [ # field2
#                 [],
#                 [],
#             ],
#         ]
#     """
#     options = models.JSONField(
#         max_length=256, null=True, blank=True, verbose_name="可选代码字符串", help_text="代码字符串, 一般为字典filter"
#     )
#
#     def __str__(self):
#         return self.content_type.app_labeled_name + ": " + ",".join(self.fields)
#
#     class Meta:
#         app_label = "account"
#         verbose_name = "数据过滤字段配置"
#         verbose_name_plural = verbose_name
#         ordering = ["-id"]


class PermissionRelation(models.Model):
    permission_a = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="relation_as_a")
    permission_b = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="relation_as_b")
    relation = models.CharField("关系", max_length=16, choices=enums.PermissionRelationEnum.choices(), help_text="组类型",)

    def __str__(self):
        return self.permission_b.codename + self.relation + self.permission_b.codename

    class Meta:
        verbose_name = "权限关系"
        verbose_name_plural = verbose_name


class Role(RemarkFieldMixin, BaseModel):
    name = models.CharField(_("name"), max_length=150, unique=True)
    system_resources = models.ManyToManyField(
        to=SystemResource, related_name="roles", help_text="系统资源", verbose_name="系统资源", blank=True,
    )
    preserved = models.BooleanField(
        verbose_name="是否系统保留角色", help_text=f"是否系统保留角色: {enums.SceneRole.values()}", default=False
    )
    # data_filters = models.ManyToManyField(
    #     to=DataFilter, related_name="roles", help_text="数据限制", verbose_name="数据限制", blank=True,
    # )

    objects = GroupManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)  # noqa

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = verbose_name


class Profile(PolyBaseModel, AbstractUser, PolymorphicModel):
    """
    username、phone
    """

    roles = models.ManyToManyField(
        Role, related_name="profiles", verbose_name="所属角色", help_text="所属角色(int)", blank=True
    )
    nickname = models.CharField(max_length=128, verbose_name="昵称", help_text="昵称", default="")
    avatar = models.FileField(verbose_name="头像", blank=True, upload_to=file_upload_to, null=True)
    gender = models.CharField(
        "性别", max_length=24, choices=enums.GenderEnum.choices(), default=enums.GenderEnum.male.value, help_text="性别"
    )
    operator = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True, default=None, help_text="操作人"
    )

    @property
    def role_names(self):
        return list(self.roles.values_list("name", flat=True))

    def has_api_perm(self, request, view):
        if self.is_active and self.is_superuser:
            return True

        return _user_has_api_perm(self, request, view)

    objects = ProfileManager()

    @classmethod
    def filter_by_permission_code(cls, permission_code, *args, **kwargs):
        return cls.objects.filter(
            models.Q(user_permissions__codename=permission_code)
            | models.Q(roles__system_resources__permissions__codename=permission_code)
        ).filter(*args, **kwargs)

    class Meta(AbstractUser.Meta):
        verbose_name = "用户"
        verbose_name_plural = verbose_name
        swappable = "AUTH_USER_MODEL"


class System(LabelFieldMixin, RemarkFieldMixin, BaseModel):
    """
    系统
    """

    code = models.CharField(verbose_name="唯一标识", max_length=16, help_text="唯一标识", unique=True)
    users = models.ManyToManyField(to=Profile, related_name="systems", help_text="用户", verbose_name="用户", blank=True,)
    system_resources = models.ManyToManyField(
        to=SystemResource, related_name="systems", help_text="系统资源", verbose_name="系统资源", blank=True,
    )
    roles = models.ManyToManyField(to=Role, related_name="systems", help_text="角色", verbose_name="角色", blank=True)

    # data_filters = models.ManyToManyField(
    #     to=DataFilter, related_name="systems", help_text="数据限制", verbose_name="数据限制", blank=True,
    # )

    class Meta:
        verbose_name = "系统"
        verbose_name_plural = verbose_name


class ProfileFieldMixin(models.Model):
    profile = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE)

    class Meta:
        abstract = True
