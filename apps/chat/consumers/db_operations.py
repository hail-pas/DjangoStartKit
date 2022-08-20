from typing import Any, Set, List, Tuple, Union, Optional, Awaitable

from channels.db import database_sync_to_async
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser

from apps.chat.models import Group, Dialog, GroupMessage, UploadedFile, DialogMessage, GroupMembership
from apps.account.models import Profile
from apps.chat.consumers import defines

ChatTypeInstanceModel = {
    defines.ChatType.Group: GroupMembership.get_group_membership,
    defines.ChatType.Dialog: Dialog.get_dialog,
}

ChatReceiverModel = {defines.ChatType.Group: Group.objects.get, defines.ChatType.Dialog: Profile.objects.get}


@database_sync_to_async
def get_chat_instance(
    chat_type: defines.ChatType, profile_id: int, receiver_id: int
) -> Awaitable[Optional[Union[GroupMembership, Dialog]]]:
    return ChatTypeInstanceModel[chat_type](profile_id, receiver_id)  # noqa


@database_sync_to_async
def get_receiver(chat_type: defines.ChatType, receiver_id: int) -> Awaitable[Union[Profile, Group]]:
    return ChatReceiverModel[chat_type](pk=receiver_id)


@database_sync_to_async
def save_group_message(group_id, profile_id, type_, value, file_id=None) -> Awaitable[GroupMessage]:
    return GroupMessage.objects.create(
        group_id=group_id, profile_id=profile_id, type=type_, value=value, file_id=file_id
    )


@database_sync_to_async
def save_dialog_message(sender_id, receiver_id, type_, value, file_id=None) -> Awaitable[DialogMessage]:
    return DialogMessage.objects.create(
        sender_id=sender_id, receiver_id=receiver_id, type=type_, value=value, file_id=file_id
    )


@database_sync_to_async
def get_group_ids_with_profile_pk(profile_id) -> Awaitable[List]:
    return GroupMembership.objects.filter(profile_id=profile_id).values_list("group_id")


@database_sync_to_async
def get_user_file_with_pk(profile_id, file_id) -> Awaitable[UploadedFile]:
    return UploadedFile.objects.filter(profile_id=profile_id, file_id=file_id).only("name", "extension", "size").first()
