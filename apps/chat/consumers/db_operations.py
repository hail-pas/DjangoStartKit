from typing import Any, Tuple, Optional, Awaitable, Set, Union

from channels.db import database_sync_to_async
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser

from apps.chat.consumers import defines
from apps.chat.models import Dialog, UploadedFile, DialogMessage, GroupMembership, Group
from apps.account.models import Profile

ChatTypeInstanceModel = {
    defines.ChatType.Group: GroupMembership.get_group_membership,
    defines.ChatType.Dialog: Dialog.create_or_update
}

ChatReceiverModel = {
    defines.ChatType.Group: Group.objects.get,
    defines.ChatType.Dialog: Profile.objects.get
}


@database_sync_to_async
def get_chat_instance(chat_type: defines.ChatType, profile_id: int, identifier: int) -> Awaitable[
    Optional[Union[GroupMembership, Dialog]]]:
    return ChatTypeInstanceModel[chat_type](profile_id, identifier)  # noqa


@database_sync_to_async
def get_receiver(chat_type: defines.ChatType, identifier: int) -> Awaitable[Union[Profile, Group]]:
    return ChatReceiverModel[chat_type](identifier)


@database_sync_to_async
def get_dialog_to_add(profile: Profile) -> set[Any]:
    return set(list(sum(Dialog.get_dialogs_for_user(profile), ())))


@database_sync_to_async
def get_dialog_by_user_pk(user__pk, _user_pk) -> Dialog:
    return Dialog.create_or_update(user__pk, _user_pk)


@database_sync_to_async
def get_user_by_pk(pk: str) -> Awaitable[Optional[AbstractBaseUser]]:
    return Profile.objects.filter(pk=pk).first()


@database_sync_to_async
def get_file_by_id(file_id: str) -> Awaitable[Optional[UploadedFile]]:
    try:
        f = UploadedFile.objects.filter(id=file_id).first()
    except ValidationError:
        f = None
    return f


@database_sync_to_async
def get_message_by_id(mid: int) -> Optional[tuple[str, str]]:
    msg: Optional[DialogMessage] = DialogMessage.objects.filter(id=mid).first()
    if msg:
        return str(msg.receiver.pk), str(msg.sender.pk)
    else:
        return None


@database_sync_to_async
def mark_message_as_read(message_id: int, sender_pk: str, receiver_pk: str):
    return DialogMessage.objects.filter(id__lte=message_id, sender_id=sender_pk, receiver_id=receiver_pk,
                                        read=False).update(read=True)


@database_sync_to_async
def mark_message_as_read(mid: int) -> Awaitable[None]:
    return DialogMessage.objects.filter(id=mid).update(read=True)


@database_sync_to_async
def get_unread_count(sender, receiver) -> int:
    return int(DialogMessage.get_unread_count(sender.id, receiver.id))


@database_sync_to_async
def save_text_message(text: str, from_: AbstractBaseUser, to: AbstractBaseUser) -> Awaitable[DialogMessage]:
    return DialogMessage.objects.create(text=text, sender=from_, recipient=to)


@database_sync_to_async
def save_file_message(file: UploadedFile, from_: AbstractBaseUser, to: AbstractBaseUser) -> Awaitable[DialogMessage]:
    return DialogMessage.objects.create(file=file, sender=from_, recipient=to)
