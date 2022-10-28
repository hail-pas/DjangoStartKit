from typing import List, Union, Optional, Awaitable

from channels.db import database_sync_to_async

from common.utils import flatten_list
from apis.chat.consumers import defines
from storages.relational.models import (
    Group,
    Config,
    Dialog,
    Profile,
    GroupMessage,
    UploadedFile,
    DialogMessage,
    GroupMembership,
)


@database_sync_to_async
def get_system_sender():
    config = Config.objects.filter(key="system_info").first()
    if not config:
        return defines.message_content.SenderInfo(id="df-lanka", avatar=None, nickname="df-lanka")
    return defines.message_content.SenderInfo(**config.value)


@database_sync_to_async
def get_chat_instance(
    chat_type: defines.chat_type.ChatType, profile_id: int, receiver_id: int
) -> Awaitable[Optional[Union[GroupMembership, Dialog]]]:
    ChatTypeInstanceModel = {
        defines.chat_type.ChatType.Group: GroupMembership.get_group_membership,
        defines.chat_type.ChatType.Dialog: Dialog.get_dialog,
    }
    return ChatTypeInstanceModel[chat_type](profile_id, receiver_id)  # noqa


@database_sync_to_async
def get_receiver(chat_type: defines.chat_type.ChatType, receiver_id: int) -> Awaitable[Union[Profile, Group]]:
    ChatReceiverModel = {
        defines.chat_type.ChatType.Group: Group.objects.get,
        defines.chat_type.ChatType.Dialog: Profile.objects.get,
    }
    return ChatReceiverModel[chat_type](pk=receiver_id)


@database_sync_to_async
def save_message(
    chat_type: defines.chat_type.ChatType,
    profile_id: int,
    related_id: int,
    message_type: defines.message_type.MessageType,
    value,
    **kwargs,
) -> Awaitable[Union[GroupMessage, DialogMessage]]:
    if chat_type == defines.chat_type.ChatType.Group:
        return GroupMessage.objects.create(group_id=related_id, profile_id=profile_id, type=message_type, value=value)
    elif chat_type == defines.chat_type.ChatType.Dialog:
        return DialogMessage.objects.create(
            sender_id=profile_id, receiver_id=related_id, type=message_type, value=value, **kwargs
        )


@database_sync_to_async
def get_group_ids_with_profile_pk(profile_id) -> Awaitable[List]:
    return flatten_list(GroupMembership.objects.filter(profile_id=profile_id).values_list("group_id"))


@database_sync_to_async
def update_unread_messages(chat_instance_id, profile_id, message_id):
    """
    message_id 之前的都已读
    """
    DialogMessage.objects.filter(
        dialog_id=chat_instance_id, sender_id=profile_id, read=False, id__lte=message_id
    ).update(read=True)


@database_sync_to_async
def get_user_file_with_pk(profile_id, file_id) -> Awaitable[UploadedFile]:
    return UploadedFile.objects.filter(profile_id=profile_id, file_id=file_id).only("id", "size").first()
