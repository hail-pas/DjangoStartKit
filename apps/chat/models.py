from typing import Any, Optional, Union

from django.db import models
from django.utils import timezone

# Create your models here.
from django.db.models import Q

from apps import enums
from common.utils import file_upload_to
from storages.mysql import BaseModel, LabelFieldMixin, StatusFieldMixin, OrderWeightFieldMixin
from apps.account.models import Profile


class ProfileFieldMixin(models.Model):
    profile = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE)

    class Meta:
        abstract = True


class UploadedFile(ProfileFieldMixin, LabelFieldMixin):
    file = models.FileField(verbose_name="文件", blank=False, null=False, upload_to=file_upload_to)
    create_time = models.DateTimeField("创建时间", auto_now_add=True, help_text="创建时间", editable=False)

    def __str__(self):
        return str(self.file.name)

    class Meta:
        verbose_name = "聊天上传文件"
        verbose_name_plural = verbose_name


class Group(BaseModel, LabelFieldMixin, OrderWeightFieldMixin):
    """
    圈子
    """

    creator = models.ForeignKey(
        to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE, related_name="created_groups"
    )
    count = models.IntegerField(verbose_name="人数", help_text="人数", default=0)
    cover = models.FileField(verbose_name="封面", blank=True, upload_to=file_upload_to)
    description = models.CharField(max_length=255, default="", verbose_name="简介", help_text="简介")
    is_official = models.BooleanField(default=False, verbose_name="是否官方圈子", help_text="是否官方圈子")

    class Meta:
        verbose_name = "圈子"
        verbose_name_plural = verbose_name
        ordering = ["-order_weight"]
        indexes = [models.Index(fields=["label"])]


class GroupMembership(BaseModel, ProfileFieldMixin, StatusFieldMixin):
    group = models.ForeignKey(to=Group, verbose_name="圈子", help_text="圈子", on_delete=models.CASCADE)

    @staticmethod
    def get_group_membership(profile_id: int, group_id: int):
        return GroupMembership.objects.filter(profile_id=profile_id, group_id=group_id, status=enums.Status.enable.value).first()

    class Meta:
        verbose_name = "圈子与用户"
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=["group"]), models.Index(fields=["profile"])]
        unique_together = (("group", "profile"),)


class GroupMessage(ProfileFieldMixin):
    """
    持久化消息
    """

    group = models.ForeignKey(to=Group, verbose_name="圈子", help_text="圈子", on_delete=models.CASCADE)
    type = models.CharField(
        "消息类型",
        max_length=16,
        choices=enums.MessageType.choices(),
        default=enums.MessageType.text.value,
        help_text="消息类型",
    )
    value = models.TextField(help_text="消息体", verbose_name="消息体")
    file = models.ForeignKey(
        UploadedFile, related_name="group_message", on_delete=models.DO_NOTHING, verbose_name="文件", blank=True,
        null=True
    )
    create_time = models.DateTimeField("创建时间", auto_now_add=True, help_text="创建时间", editable=False, db_index=True)

    class Meta:
        verbose_name = "群聊消息记录"
        verbose_name_plural = verbose_name
        ordering = ["-id"]


class Dialog(BaseModel, StatusFieldMixin):
    left_user = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE,
                                  related_name="as_left_user")  # noqa
    right_user = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE,
                                   related_name="as_right_user")

    def __str__(self):
        return f"{self.left_user.username} - {self.right_user.username}"

    @classmethod
    def dialog_exists(cls, left_user_id: int, right_user_id: int) -> Optional["Dialog"]:
        return cls.objects.filter(
            Q(left_user_id=left_user_id, right_user_id=right_user_id) | Q(left_user_id=right_user_id,
                                                                          right_user_id=left_user_id)
        ).first()

    @classmethod
    def create_or_update(cls, left_user_id: int, right_user_id: int) -> "Dialog":
        exists = cls.dialog_exists(left_user_id, right_user_id)
        if not exists:
            exists = cls.objects.create(left_user_id=left_user_id, right_user_id=right_user_id)
        else:
            if exists.status != enums.Status.enable.value:
                exists.update_time = timezone.now()
                exists.status = enums.Status.enable.value
                exists.save(update_fields=["update_time", "status"])

        return exists

    @staticmethod
    def get_dialogs_for_user(user: Profile):
        return Dialog.objects.filter(Q(left_user=user) | Q(right_user=user)).values_list("left_user_id",
                                                                                         "right_user_id")

    class Meta:
        unique_together = (("left_user", "right_user"), ("right_user", "left_user"))
        verbose_name = "私聊"
        verbose_name_plural = verbose_name


class DialogMessage(models.Model):
    sender = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE,
                               related_name="sent_message")
    receiver = models.ForeignKey(to=Profile, verbose_name="用户", help_text="用户", on_delete=models.CASCADE,
                                 related_name="received_message")
    type = models.CharField(
        "消息类型",
        max_length=16,
        choices=enums.MessageType.choices(),
        default=enums.MessageType.text.value,
        help_text="消息类型",
    )
    value = models.TextField(help_text="消息体", verbose_name="消息体")
    file = models.ForeignKey(
        UploadedFile, related_name="dialog_message", on_delete=models.DO_NOTHING, verbose_name="文件", blank=True,
        null=True
    )
    create_time = models.DateTimeField("创建时间", auto_now_add=True, help_text="创建时间", editable=False, db_index=True)
    read = models.BooleanField(verbose_name="是否已读", default=False, help_text="是否已读")

    @staticmethod
    def get_unread_count(sender_id, receiver_id):
        return DialogMessage.objects.filter(sender_id=sender_id, receiver_id=receiver_id, read=False).count()

    @staticmethod
    def get_last_messages(sender_id, receiver_id, count=20):
        return (
            DialogMessage.objects.filter(
                Q(sender_id=sender_id, receiver_id=receiver_id) | Q(sender_id=receiver_id, receiver_id=sender_id)
            )
            .select_related("sender", "receiver")
            .order_by("-id")[:count]
        )

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ["-id"]
        verbose_name = "私聊消息记录"
        verbose_name_plural = verbose_name
