import logging
from abc import ABC
from typing import Optional, Union, Set
from urllib.parse import parse_qsl

import ujson
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels_redis.core import RedisChannelLayer

from apps.account.models import Profile
from apps.chat.consumers import defines
from apps.chat.consumers.db_operations import get_chat_instance, get_receiver
from apps.chat.consumers.decorator import authenticate_required
from apps.chat.models import Dialog, GroupMembership, Group

logger = logging.getLogger("consumer.mixins")

ChatTypeUniqueFormatter = {
    defines.ChatType.Group: defines.ChatUniqueFormatKey.Group,
    defines.ChatType.Dialog: defines.ChatUniqueFormatKey.Dialog

}


class AsyncUJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def decode_json(cls, text_data):
        return ujson.loads(text_data)

    @classmethod
    async def encode_json(cls, content):
        return ujson.dumps(content)

    async def interrupt(self, code: defines.ServiceCode):
        logger.debug("interrupting.....")
        await self.disconnect(code.value)
        raise StopConsumer()
    # to disconnect


class ConnectPrepareMixin(AsyncUJsonWebsocketConsumer):
    """
    连接准备工作
    """
    profile: Profile = None
    receiver: Union[Profile, Group] = None
    chat_type: defines.ChatType
    chat_instance: Union[Dialog, GroupMembership]
    chat_unique_id: str
    channel_layer: RedisChannelLayer
    support_chat_type: Set = {defines.ChatType.Dialog.value, defines.ChatType.Group.value}

    @authenticate_required()
    async def pre_accept(self):
        logger.debug("pre_accepting....")
        profile = self.scope["user"]
        self.profile = profile
        # chat_type = self.scope["url_route"]["kwargs"]["chat_type"]
        # if chat_type not in self.support_chat_type:
        #     await self.interrupt(code=defines.ServiceCode.UnSupportedChatType)
        # chat_type = defines.ChatType(chat_type)
        identifier = self.scope["url_route"]["kwargs"]["identifier"]
        chat_instance = await get_chat_instance(self.chat_type, self.profile.pk, identifier)
        if not chat_instance:
            await self.interrupt(code=defines.ServiceCode.ReceiverNotExists)
        self.receiver = await get_receiver(identifier)
        self.chat_instance = chat_instance
        # self.chat_type = chat_type
        self.chat_unique_id = ChatTypeUniqueFormatter[self.chat_type] % (self.profile.pk, self.chat_instance.id)

    async def post_accept(self):
        pass

    async def connect(self):
        await self.pre_accept()
        await self.accept()
        await self.post_accept()

    async def disconnect(self, close_code):
        logger.debug("disconnecting...")
        if close_code not in [defines.ServiceCode.Unauthorized.value, defines.ServiceCode.UnSupportedChatType.value]:
            # 用户离线
            logger.info(
                f"User {self.profile.pk} disconnected, removing channel {self.channel_name} from group {self.chat_unique_id}"
            )
            await self.channel_layer.group_discard(self.chat_unique_id, self.channel_name)
            # 离线
            # dialogs = await get_groups_to_add(self.user)
            # logger.info(f"User {self.user.pk} disconnected, sending 'user_went_offline' to {dialogs} dialog groups")
            # for d in dialogs:
            #     await self.channel_layer.group_send(str(d),
            #                                         OutgoingEventWentOffline(user_pk=str(self.user.pk))._asdict())


class ReplyMixin(ConnectPrepareMixin, ABC):
    """
    消息回复
    """

    def gen_reply(self, type_, payload=None):
        reply = ujson.dumps(
            defines.ServiceReplyData(
                type=type_,
                payload=payload,
                connection_info=defines.ConnectionInfo(chat_type=self.chat_type, chat_unique_id=self.chat_unique_id,
                                                       channel_name=self.channel_name)
            )
        )
        logger.debug(f"reply data is: {reply}")
        return reply.encode()

    async def send_error(self, code: defines.ServiceCode, message: Optional[str]):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Error,
                                      defines.PayloadError(code=code, message=message, sender=defines.SystemInfo))
        )

    async def send_text(self, sender: defines.SenderInfo, text: str):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Text,
                                      defines.PayloadText(code=defines.ServiceCode.Success, value=text, sender=sender))
        )

    async def send_file(self, sender: defines.SenderInfo, type_: Union[defines.MessageType.Picture,], id: int, url: str,
                        name: str, size: int, extension: str):
        await self.send(
            bytes_data=self.gen_reply(type_,
                                      defines.PayLoadFile(code=defines.ServiceCode.Success, sender=sender, id=id,
                                                          url=url, name=name, size=size, extension=extension))
        )

    async def send_online(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Online,
                                      defines.PayloadOnline(code=defines.ServiceCode.Success,
                                                            sender=defines.SystemInfo, user_info=user_info))
        )

    async def send_offline(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Offline,
                                      defines.PayloadOffline(code=defines.ServiceCode.Success,
                                                             sender=defines.SystemInfo, user_info=user_info))
        )

    async def send_join(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Join,
                                      defines.PayloadJoin(code=defines.ServiceCode.Success, sender=defines.SystemInfo,
                                                          user_info=user_info))
        )

    async def send_typing(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.Typing,
                                      defines.PayloadTyping(code=defines.ServiceCode.Success,
                                                            sender=defines.SystemInfo, user_info=user_info))
        )

    async def send_stop_typing(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.StopTyping,
                                      defines.PayloadStopTyping(code=defines.ServiceCode.Success,
                                                                sender=defines.SystemInfo, user_info=user_info))
        )

    async def send_message_read(self, message_id: int, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.MessageRead,
                                      defines.PayloadMessageRead(code=defines.ServiceCode.Success,
                                                                 message_id=message_id, sender=defines.SystemInfo,
                                                                 user_info=user_info))
        )

    async def send_message_sent(self, message_id: int):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.MessageSent,
                                      defines.PayloadMessageSent(code=defines.ServiceCode.Success,
                                                                 message_id=message_id, sender=defines.SystemInfo))
        )

    async def send_new_un_read_count(self, connection_info: defines.ConnectionInfo, count: int, message_id: int):
        await self.send(
            bytes_data=self.gen_reply(defines.MessageType.MessageNewUnRead,
                                      defines.PayloadMessageNewUnRead(code=defines.ServiceCode.Success,
                                                                      connection_info=connection_info, count=count,
                                                                      message_id=message_id, sender=defines.SystemInfo))
        )


class ServerReply(ReplyMixin, ABC):
    """
    消息处理
    """

    async def receive_json(self, content, **kwargs):
        await self.handle_dispatch(content, **kwargs)

    async def handle_dispatch(self, content, **kwargs):
        logger.debug(content)
        logger.debug(kwargs)
        await self.send_text(sender=defines.SystemInfo, text=content["value"])

    async def post_handle(self, *args, **kwargs):
        pass
