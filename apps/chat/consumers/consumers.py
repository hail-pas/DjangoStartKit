import json
import logging
from abc import ABC
from typing import Dict, Tuple, Optional, Union

import ujson
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AbstractBaseUser

from apps.chat.consumers.decorator import authenticate_required
from apps.chat.consumers.mixins import ServerReply
from storages.redis import RedisUtil, keys
from apps.chat.models import Dialog, UploadedFile, DialogMessage
from apps.account.models import Profile
from apps.chat.consumers import defines
from apps.chat.serializers import serialize_file_model
from apps.chat.consumers.db_operations import (
    get_file_by_id,
    get_user_by_pk,
    get_unread_count,
    get_message_by_id,
    save_file_message,
    save_text_message,
    mark_message_as_read,
    get_dialog_by_user_pk,
)

logger = logging.getLogger("__name__")


class SystemCenterConsumer(ServerReply):
    """
    未读信息数量、在线状态
    20s 发一次数据， 25s的在线超时时间
    """
    pass


class GroupChatConsumer(ServerReply):
    """
    组聊天
    """
    chat_type = defines.ChatType.Group
    group_name: str = None

    def pre_accept(self):
        self.group_name = defines.RoomNameUniqueFormatKey.Group % self.chat_instance.id
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)


class DialogConsumer(ServerReply):
    chat_type = defines.ChatType.Dialog
    dialog_name: str = None

    def pre_accept(self):
        self.dialog_name = defines.RoomNameUniqueFormatKey.Dialog % self.chat_instance.id
        async_to_sync(self.channel_layer.group_add)(self.dialog_name, self.channel_name)
