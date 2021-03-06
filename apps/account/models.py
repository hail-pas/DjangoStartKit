# Create your models here.
import string

from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.db.models import Manager
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission, GroupManager, _user_has_perm, _user_has_module_perms  # noqa
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.contenttypes.models import ContentType

from apps import enums
from storages.mysql import BaseModel, LabelFieldMixin, RemarkFieldMixin
from common.django.perms import _user_has_api_perm  # noqa

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
        return self.get(**{self.model.USERNAME_FIELD: username})


class ProfileManager(BaseUserManager):
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

    username = models.CharField(_("?????????"), max_length=128, help_text="?????????, ??????128",)
    phone = models.CharField(
        "??????", max_length=11, unique=True, help_text="??????", error_messages={"unique": "????????????????????????????????????"}
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
?????? - ?????????????????????????????? - ????????????????????? - ??????????????????????????????????????????
?????????????????????????????????????????? ????????????????????? ??????????????????????????????????????????????????????
    ??????
    ??????
    ??????
    ???????????????/??????/?????????
    ????????????
    ????????????
    ??????
    ??????
??????????????????????????????????????????????????????
    ??????
    ContentType
    # TODO: ?????????????????????
    ???????????????????????????????????????????????????????????????, ????????????????????????????????????????????????
    ??????
    ??????
"""


class SystemResource(LabelFieldMixin, RemarkFieldMixin, BaseModel):
    """
    ????????????
    """

    parent = models.ForeignKey(
        to="self",
        related_name="children",
        on_delete=models.CASCADE,
        verbose_name="??????",
        help_text="??????",
        blank=True,
        null=True,
    )
    reference_to = models.ForeignKey(
        to="self",
        related_name="reference_from",
        on_delete=models.SET_NULL,
        verbose_name="??????????????????",
        help_text="??????????????????",
        blank=True,
        null=True,
    )
    code = models.CharField("????????????", max_length=64, help_text="????????????",)
    route_path = models.CharField("????????????", max_length=128, help_text="????????????", null=True, blank=True)
    icon_path = models.CharField("??????", max_length=128, help_text="??????", null=True, blank=True)
    type = models.CharField("????????????", max_length=16, choices=enums.SystemResourceTypeEnum.choices(), help_text="?????????",)
    order_num = models.IntegerField("????????????", default=1, help_text="????????????",)
    enabled = models.BooleanField("????????????", default=True, help_text="????????????????????????")
    assignable = models.BooleanField("???????????????", default=True, help_text="????????????????????????")
    permissions = models.ManyToManyField(Permission, verbose_name="??????", help_text="??????", blank=True)

    @classmethod
    def root_menus(cls, profile):
        menus = cls.objects.filter(
            parent=None, enabled=True, type=enums.SystemResourceTypeEnum.menu.value, systems__in=[profile.system]
        )
        return menus

    def __str__(self):
        return f"{self.parent.label + '-' if self.parent else ''}" + self.label

    class Meta:
        verbose_name = "????????????"
        verbose_name_plural = verbose_name
        permissions = enums.PermissionEnum.choices()
        unique_together = ("code", "parent")
        ordering = ["order_num"]


class DataFilter(RemarkFieldMixin, BaseModel):
    label = models.CharField(verbose_name="??????", max_length=32, help_text="??????", unique=True)
    content_type = models.ForeignKey(
        to=ContentType, on_delete=models.CASCADE, related_name="data_filters", verbose_name="????????????", help_text="????????????",
    )
    eval_string = models.CharField(max_length=256, null=True, blank=True, verbose_name="???????????????", help_text="???????????????, ???Q??????")
    """
    eval_string_prototype = "Q({field1}) & Q({field2}) | Q({field3})"
    eval_string = eval_string_prototype.format(**{"field1": value1, })
    """
    eval_string_prototype = models.CharField(max_length=512, verbose_name="?????????????????????", help_text="?????????????????????")
    field = models.JSONField("?????????????????????", default=list, blank=True, help_text="?????????????????????")
    """
    [
        [ # field1
            ["label", "value1"],
            ["label", "value2"],
        ],
        [ # field2
            [],
            [],
        ],
    ]
    """
    options = models.JSONField(
        max_length=256, default=list, blank=True, verbose_name="????????????????????????", help_text="???????????????, ???????????????filter"
    )

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "????????????Q??????"
        verbose_name_plural = verbose_name
        ordering = ["-id"]


class DataFilterFields(LabelFieldMixin, RemarkFieldMixin, BaseModel):
    content_type = models.ForeignKey(
        to=ContentType, on_delete=models.CASCADE, related_name="data_sources", verbose_name="????????????", help_text="????????????"
    )
    fields = models.JSONField("???????????????", default=list, blank=True, help_text="???????????????")
    """
        [
            [ # field1
                ["label", "value1"],
                ["label", "value2"],
            ],
            [ # field2
                [],
                [],
            ],
        ]
    """
    options = models.JSONField(
        max_length=256, null=True, blank=True, verbose_name="?????????????????????", help_text="???????????????, ???????????????filter"
    )

    def __str__(self):
        return self.content_type.app_labeled_name + ": " + ",".join(self.fields)

    class Meta:
        verbose_name = "????????????????????????"
        verbose_name_plural = verbose_name
        ordering = ["-id"]


class PermissionRelation(models.Model):
    permission_a = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="relation_as_a")
    permission_b = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="relation_as_b")
    relation = models.CharField("??????", max_length=16, choices=enums.PermissionRelationEnum.choices(), help_text="?????????",)

    def __str__(self):
        return self.permission_b.codename + self.relation + self.permission_b.codename

    class Meta:
        verbose_name = "????????????"
        verbose_name_plural = verbose_name


class Role(RemarkFieldMixin, BaseModel):
    name = models.CharField(_("name"), max_length=150, unique=True)
    system_resources = models.ManyToManyField(
        to=SystemResource, related_name="roles", help_text="????????????", verbose_name="????????????", blank=True,
    )
    data_filters = models.ManyToManyField(
        to=DataFilter, related_name="roles", help_text="????????????", verbose_name="????????????", blank=True,
    )

    objects = GroupManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)  # noqa

    class Meta:
        verbose_name = "??????"
        verbose_name_plural = verbose_name


class Profile(BaseModel, AbstractUser):
    """
    username???phone
    """

    roles = models.ManyToManyField(
        Role, related_name="profiles", verbose_name="????????????", help_text="????????????(int)", blank=True
    )
    gender = models.CharField(
        "??????", max_length=24, choices=enums.GenderEnum.choices(), default=enums.GenderEnum.male.value, help_text="??????"
    )
    operator = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True, default=None, help_text="?????????"
    )
    display_fields_config = models.JSONField("?????????????????????JSON", default=dict, blank=True, help_text="?????????????????????JSON")

    @property
    def role_codes(self):
        return self.roles.values_list("code").all()

    @property
    def role_names(self):
        return self.roles.values_list("name").all()

    def has_api_perm(self, request, view):
        if self.is_active and self.is_superuser:
            return True

        return _user_has_api_perm(self, request, view)

    objects = ProfileManager()

    class Meta(AbstractUser.Meta):
        verbose_name = "??????"
        verbose_name_plural = verbose_name
        swappable = "AUTH_USER_MODEL"


class System(LabelFieldMixin, RemarkFieldMixin, BaseModel):
    """
    ??????
    """

    code = models.CharField(verbose_name="????????????", max_length=16, help_text="????????????", unique=True)
    users = models.ManyToManyField(to=Profile, related_name="systems", help_text="??????", verbose_name="??????", blank=True,)
    system_resources = models.ManyToManyField(
        to=SystemResource, related_name="systems", help_text="????????????", verbose_name="????????????", blank=True,
    )
    data_filters = models.ManyToManyField(
        to=DataFilter, related_name="systems", help_text="????????????", verbose_name="????????????", blank=True,
    )

    class Meta:
        verbose_name = "??????"
        verbose_name_plural = verbose_name
