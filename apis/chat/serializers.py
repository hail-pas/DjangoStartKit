import os
from typing import Dict, Optional

from storages.mysql import models
from common.drf.serializers import CustomModelSerializer
from apis.account.serializers import ProfileSimpleSerializer
from storages.mysql.models.chat import UploadedFile
from storages.mysql.models.account import Profile


class GroupMessageSerializer(CustomModelSerializer):
    profile = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = models.GroupMessage
        fields = "__all__"


class DialogSerializer(CustomModelSerializer):
    left_user = ProfileSimpleSerializer(read_only=True)
    right_user = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = models.Dialog
        fields = "__all__"


class DialogMessageSerializer(CustomModelSerializer):
    profile = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = models.DialogMessage
        fields = "__all__"


def serialize_file_model(m: UploadedFile) -> Dict[str, str]:
    return {"id": str(m.id), "url": m.file.url, "size": m.file.size, "name": os.path.basename(m.file.name)}


def serialize_message_model(m: models.DialogMessage, user_id):
    sender_pk = m.sender.pk
    is_out = sender_pk == user_id
    # TODO: add forwards
    # TODO: add replies
    obj = {
        "id": m.id,
        "value": m.value,
        "create_time": m.create_time,
        "read": m.read,
        "file": serialize_file_model(m.file) if m.file else None,
        "sender": str(sender_pk),
        "out": is_out,
        "sender_username": m.sender.get_username(),
    }
    return obj


def serialize_dialog_model(m: models.Dialog, user_id):
    username_field = Profile.USERNAME_FIELD
    other_user_pk, other_user_username = (
        Profile.objects.filter(pk=m.left_user.pk).values_list("pk", username_field).first()
        if m.right_user.pk == user_id
        else Profile.objects.filter(pk=m.right_user.pk).values_list("pk", username_field).first()
    )
    unread_count = models.DialogMessage.get_unread_count(sender_id=other_user_pk, receiver_id=user_id)
    last_message: Optional[models.DialogMessage] = models.DialogMessage.get_last_messages(
        sender_id=other_user_pk, receiver_id=user_id
    )
    last_message_ser = serialize_message_model(last_message, user_id) if last_message else None
    obj = {
        "id": m.id,
        "create_time": m.create_time,
        "update_time": m.update_time,
        "other_user_id": str(other_user_pk),
        "unread_count": unread_count,
        "username": other_user_username,
        "last_message": last_message_ser,
    }
    return obj
