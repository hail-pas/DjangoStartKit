from typing import List, Union, Optional, Awaitable

from channels.db import database_sync_to_async

from apps.chat.models import Group, Dialog, GroupMessage, UploadedFile, DialogMessage, GroupMembership
from apps.info.models import Config
from apps.account.models import Profile
from apps.chat.consumers import defines
from apps.chat.consumers.defines import chat_type, message_type
from apps.chat.consumers.defines.message_content import SenderInfo

ChatTypeInstanceModel = {
    chat_type.ChatType.Group: GroupMembership.get_group_membership,
    chat_type.ChatType.Dialog: Dialog.get_dialog,
}

ChatReceiverModel = {chat_type.ChatType.Group: Group.objects.get, chat_type.ChatType.Dialog: Profile.objects.get}


@database_sync_to_async
def get_system_sender():
    config = Config.objects.filter(key="system_info").first()
    if not config:
        return SenderInfo(id="df-lanka", avatar=None, nickname="df-lanka")
    return SenderInfo(**config.value)


@database_sync_to_async
def get_chat_instance(
    chat_type: chat_type.ChatType, profile_id: int, receiver_id: int
) -> Awaitable[Optional[Union[GroupMembership, Dialog]]]:
    return ChatTypeInstanceModel[chat_type](profile_id, receiver_id)  # noqa


@database_sync_to_async
def get_receiver(chat_type: chat_type.ChatType, receiver_id: int) -> Awaitable[Union[Profile, Group]]:
    return ChatReceiverModel[chat_type](pk=receiver_id)


@database_sync_to_async
def save_message(
    chat_type: chat_type.ChatType, profile_id: int, related_id: int, message_type: message_type.MessageType, value
) -> Awaitable[Union[GroupMessage, DialogMessage]]:
    if chat_type == defines.chat_type.ChatType.Group:
        return GroupMessage.objects.create(group_id=related_id, profile_id=profile_id, type=message_type, value=value)
    elif chat_type == defines.chat_type.ChatType.Dialog:
        return DialogMessage.objects.create(
            sender_id=profile_id, receiver_id=related_id, type=message_type, value=value
        )


@database_sync_to_async
def get_group_ids_with_profile_pk(profile_id) -> Awaitable[List]:
    return GroupMembership.objects.filter(profile_id=profile_id).values_list("group_id")


@database_sync_to_async
def get_user_file_with_pk(profile_id, file_id) -> Awaitable[UploadedFile]:
    return UploadedFile.objects.filter(profile_id=profile_id, file_id=file_id).only("name", "extension", "size").first()
