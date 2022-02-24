# Create your models here.
from django.db import models
from django.contrib.auth.models import Permission, GroupManager
from django.db.models import Manager
from django.utils.crypto import get_random_string
from storages.mysql import BaseModel, DeletedFieldManager
from apps import enums
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import (
    Permission,
    _user_get_permissions,  # noqa
    _user_has_perm,  # noqa
    _user_has_module_perms,  # noqa
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

allowed_chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789'


class BaseUserManager(Manager):

    @classmethod
    def normalize_email(cls, email):
        """
        Normalize the email address by lowercasing the domain part of it.
        """
        email = email or ''
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            email = email_name + '@' + domain_part.lower()
        return email

    def make_random_password(self, length=10, allowed_chars=allowed_chars):
        """
        Generate a random password with the given length and given
        allowed_chars. The default value of allowed_chars does not have "I" or
        "O" or letters and digits that look similar -- just to avoid confusion.
        """
        return get_random_string(length, allowed_chars)

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})


class ProfileManager(BaseUserManager):
    def create_user(self, username, phone, password, **extra_fields):
        user = self.model(username=username, phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, phone, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(username, phone, password, **extra_fields)


# 使用自定义权限组
class PermissionsMixin(models.Model):
    """
    Add the fields and methods necessary to support the Group and Permission
    models using the ModelBackend.
    """
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )
    groups = models.ManyToManyField(
        "CustomizeGroup",
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="user_set",
        related_query_name="user",
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has directly.
        Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, 'user')

    def get_group_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has through their
        groups. Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, 'group')

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, 'all')

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
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
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('用户名'),
        max_length=128,
        help_text="用户名, 最长128",
    )
    phone = models.CharField(
        '电话',
        max_length=11,
        unique=True,
        help_text=u'电话',
        error_messages={'unique': "使用该手机号的用户已存在"}
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['username', "password"]

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


# ========================================================================

class CustomizeGroup(BaseModel):
    parents = models.ManyToManyField(
        to='self',
        through="GroupRelation",
        verbose_name="父组",
        help_text='父节点的ID',
    )
    code = models.CharField(
        '标识编码',
        max_length=64,
        help_text='标识编码',
    )
    name = models.CharField("name", max_length=150, help_text="组名")
    path = models.CharField("前端路由", max_length=128, help_text="前端路由", null=True, blank=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="权限",
        help_text="权限",
        blank=True,
    )
    group_type = models.CharField(
        '组类型',
        max_length=16,
        choices=enums.GroupTypeEnum.choices(),
        blank=True,
        null=True,
        default=enums.GroupTypeEnum.menu.value,
        help_text='组类型',
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

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    objects = GroupManager()

    @classmethod
    def _get_permission_ids(cls):
        return CustomizeGroup.objects.filter(
            group_type=enums.GroupTypeEnum.permission.value
        ).values_list("id", flat=True)

    @classmethod
    def permission_groups(cls):
        return cls.objects.filter(id__in=cls._get_permission_ids())

    @classmethod
    def _get_top_ids(cls):
        return set(cls._get_permission_ids()) - set(GroupRelation.objects.all().values_list("child_id", flat=True))

    @classmethod
    def top_groups(cls):
        return cls.objects.filter(id__in=cls._get_top_ids(), enabled=True)

    @classmethod
    def _get_menu_level1_ids(cls):
        return GroupRelation.objects.filter(parent_id__in=cls._get_top_ids()).values_list("child_id", flat=True)

    @classmethod
    def menu_level1_groups(cls):
        return cls.objects.filter(id__in=cls._get_menu_level1_ids(), enabled=True)

    @classmethod
    def menu_level2_groups(cls):
        return cls.objects.filter(
            id__in=GroupRelation.objects.filter(parent__in=cls._get_menu_level1_ids(), enabled=True).values_list(
                "child_id", flat=True))

    class Meta:
        verbose_name = u'自定义分组'
        verbose_name_plural = verbose_name
        permissions = enums.PermissionTypeEnum.choices() + enums.MenuLevel2.choices() + enums.PermissionEnum.choices()
        unique_together = ("code", "name")
        ordering = ["order_num"]


class GroupRelation(models.Model):
    parent = models.ForeignKey(CustomizeGroup, on_delete=models.CASCADE, related_name="parent_set")
    child = models.ForeignKey(CustomizeGroup, on_delete=models.CASCADE, related_name="children")

    class Meta:
        verbose_name = u'分组层级关系'
        verbose_name_plural = verbose_name


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
        error_messages={'unique': "使用该名称的角色已存在"}
    )
    groups = models.ManyToManyField(
        CustomizeGroup,
        related_name="roles",
        verbose_name='角色分组',
        help_text='角色分组',
    )
    operate_groups = models.JSONField(default=list, verbose_name="操作权限", help_text="操作权限")
    view_groups = models.JSONField(default=list, verbose_name="查看权限", help_text="查看权限")
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


class Profile(BaseModel, AbstractUser):
    """
    username、phone
    """
    roles = models.ManyToManyField(
        Role,
        related_name="profiles",
        verbose_name='所属角色',
        help_text=u'所属角色(int)',
    )
    gender = models.CharField(
        "性别",
        max_length=24,
        choices=enums.GenderEnum.choices(),
        default=enums.GenderEnum.male.value,
        help_text="性别"
    )
    operator = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        help_text='操作人'
    )
    display_fields_config = models.JSONField(
        "自定义字段配置JSON",
        default=dict,
        help_text="自定义字段配置JSON"
    )

    @property
    def role_codes(self):
        return self.roles.values_list("code").all()

    @property
    def role_names(self):
        return self.roles.values_list("name").all()

    objects = ProfileManager()

    class Meta(AbstractUser.Meta):
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        swappable = 'AUTH_USER_MODEL'
