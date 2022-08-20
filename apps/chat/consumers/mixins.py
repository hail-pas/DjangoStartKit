import logging
from abc import ABC
from typing import Union, Optional

import ujson
from channels.exceptions import StopConsumer
from channels_redis.core import RedisChannelLayer
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from storages.redis import AsyncRedisUtil, keys
from apps.chat.models import Group
from apps.account.models import Profile
from apps.chat.consumers import defines
from apps.chat.consumers.decorator import authenticate_required
from apps.chat.consumers.db_operations import get_group_ids_with_profile_pk

logger = logging.getLogger("consumer.mixins")


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


class ConnectManageConsumer(AsyncUJsonWebsocketConsumer):
    """
    连接准备工作
    """

    profile: Profile
    device_code: defines.DeviceCode
    receiver: Union[Profile, Group, defines.SenderInfo]
    channel_layer: RedisChannelLayer
    channel_name: str

    @authenticate_required()
    async def pre_accept(self):
        profile = self.scope["user"]
        self.profile = profile
        device_code = self.scope["url_route"]["kwargs"]["device_code"]
        if device_code not in [defines.DeviceCode.mobile.value, defines.DeviceCode.web.value]:
            logger.warning(f"{profile.id} connect with unknown device_code: {device_code}")
            await self.interrupt(code=defines.ServiceCode.DeviceRestrict)
        self.device_code = defines.DeviceCode(device_code)
        if await AsyncRedisUtil.r.get(
            keys.RedisCacheKey.ProfileConnectionKey.format(profile_id=self.profile.id, device_code=device_code)
        ):
            # 已建立连接
            logger.warning(f"{profile.id} connect with duplicate device_code: {device_code}")
            await self.interrupt(code=defines.ServiceCode.DeviceRestrict)

    async def post_accept(self):
        # 设置在线
        await AsyncRedisUtil.r.setbit(
            keys.RedisCacheKey.ProfileOnlineKey.format(profile_id=self.profile.id), self.profile.id, 1
        )
        # 添加连接信息，防止重复连接
        await AsyncRedisUtil.r.set(
            keys.RedisCacheKey.ProfileConnectionKey.format(
                profile_id=self.profile.id, device_code=self.device_code.value
            ),
            self.channel_name,
            expire=65,
        )
        # 加入系统群组
        await self.channel_layer.group_add(defines.ChatContextFormatKey.SystemCenter.value, self.channel_name)
        # 加入用户的群组
        for group_id in await AsyncRedisUtil.r.smembers(
            keys.RedisCacheKey.ProfileGroupSet.format(profile_id=self.profile.id), encoding="utf-8"
        ):
            await self.channel_layer.group_add(
                defines.ChatContextFormatKey.Group.value % int(group_id), self.channel_name
            )
        logger.info(f"User {self.profile.id} connected with device_code: {self.device_code}")

    async def connect(self):
        await self.pre_accept()
        await self.accept()
        await self.post_accept()

    async def disconnect(self, close_code):
        if close_code not in [defines.ServiceCode.Unauthorized.value, defines.ServiceCode.DeviceRestrict.value]:
            # 用户离线
            logger.info(
                f"User {self.profile.pk} device {self.device_code.value} disconnected, removing channel {self.channel_name}"
            )
            # 离开系统群组
            await self.channel_layer.group_discard(defines.ChatContextFormatKey.SystemCenter.value, self.channel_name)

            # 离开用户群组
            for group_id in await AsyncRedisUtil.r.smembers(
                keys.RedisCacheKey.ProfileGroupSet.format(profile_id=self.profile.id), encoding="utf-8"
            ):
                await self.channel_layer.group_discard(
                    defines.ChatContextFormatKey.Group.value % int(group_id), self.channel_name
                )
            # 删除连接信息
            await AsyncRedisUtil.r.delete(
                keys.RedisCacheKey.ProfileConnectionKey.format(
                    profile_id=self.profile.id, device_code=self.device_code.value
                )
            )

            # TODO: 多设备的离线判断
            await AsyncRedisUtil.r.setbit(
                keys.RedisCacheKey.ProfileOnlineKey.format(profile_id=self.profile.id), self.profile.id, 0
            )


class ReplyMixin(ConnectManageConsumer, ABC):
    """
    消息回复
    """

    # Receive message from the group
    async def group_message(self, message: defines.ChannelsMessageData):
        # Send message to WebSocket
        logger.debug(f"message is: {message}")
        await self.send(bytes_data=ujson.dumps(message["payload"]).encode())

    def gen_reply_bytes(self, context, chat_type, sender_info, type_, payload=None):
        return ujson.dumps(self.gen_reply(context, chat_type, sender_info, type_, payload)).encode()

    @staticmethod
    def gen_reply(context, chat_type, sender_info, type_, payload=None):
        reply_data = defines.ServiceReplyData(
            context=context, chat_type=chat_type, sender=sender_info, type=type_, payload=payload,
        )
        logger.debug(f"reply data is: {reply_data}")
        return reply_data

    def gen_sender_info(self, is_system: bool = False) -> defines.SenderInfo:
        if is_system:
            return defines.SystemInfo
        avatar = ""
        # 数据库的信息更新不会同步到 consumer 中的 profile
        # 不缓存直接获取 或者 使用 redis
        if self.profile.avatar:
            avatar = self.profile.avatar.url
        return defines.SenderInfo(id=str(self.profile.id), avatar=avatar, nickname=self.profile.nickname)

    @staticmethod
    def gen_error_payload(code: defines.ServiceCode, message: Optional[str]):
        return defines.PayloadError(code=code, message=message)

    async def send_error(self, code: defines.ServiceCode, message: Optional[str]):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                context=defines.ChatContextFormatKey.SystemCenter.value,
                chat_type=defines.ChatType.SystemCenter.value,
                sender_info=defines.SystemInfo,
                type_=defines.MessageType.Error.value,
                payload=self.gen_error_payload(code, message),
            )
        )

    @staticmethod
    def gen_text_payload(text: str):
        return defines.PayloadText(code=defines.ServiceCode.Success, value=text)

    async def send_text(self, context, chat_type, sender_info, text: str):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                context, chat_type, sender_info, defines.MessageType.Text.value, self.gen_text_payload(text)
            )
        )

    async def send_file(
        self,
        context,
        chat_type,
        sender_info: defines.SenderInfo,
        type_: Union[defines.MessageType.Picture],
        id_: int,
        url: str,
        name: str,
        size: int,
        extension: str,
    ):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                context,
                chat_type,
                sender_info,
                type_,
                defines.PayLoadFile(
                    code=defines.ServiceCode.Success.value, id=id_, url=url, name=name, size=size, extension=extension
                ),
            )
        )

    async def send_online(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.Online.value,
                defines.PayloadOnline(code=defines.ServiceCode.Success.value, user_info=user_info),
            )
        )

    async def send_offline(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.Offline.value,
                defines.PayloadOffline(code=defines.ServiceCode.Success.value, user_info=user_info),
            )
        )

    async def send_join(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.Join.value,
                defines.PayloadJoin(code=defines.ServiceCode.Success.value, user_info=user_info),
            )
        )

    async def send_typing(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.Typing.value,
                defines.PayloadTyping(code=defines.ServiceCode.Success.value, user_info=user_info),
            )
        )

    async def send_stop_typing(self, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.StopTyping.value,
                defines.PayloadStopTyping(code=defines.ServiceCode.Success.value, user_info=user_info),
            )
        )

    async def send_message_read(self, message_id: int, user_info: defines.BaseIdentifierInfo):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.MessageRead.value,
                defines.PayloadMessageRead(
                    code=defines.ServiceCode.Success.value, message_id=message_id, user_info=user_info
                ),
            )
        )

    async def send_message_sent(self, message_id: int):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter.value,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.MessageSent.value,
                defines.PayloadMessageSent(code=defines.ServiceCode.Success.value, message_id=message_id,),
            )
        )

    async def send_new_un_read_count(self, connection_info: defines.ConnectionInfo, count: int, message_id: int):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                defines.ChatContextFormatKey.SystemCenter,
                defines.ChatType.SystemCenter.value,
                defines.SystemInfo,
                defines.MessageType.MessageNewUnRead.value,
                defines.PayloadMessageNewUnRead(
                    code=defines.ServiceCode.Success.value,
                    connection_info=connection_info,
                    count=count,
                    message_id=message_id,
                ),
            )
        )


class ServerReply(ReplyMixin, ABC):
    """
    消息处理
    """

    handler = None  # BaseHandler

    async def receive_json(self, content, **kwargs):
        await self.pre_handle(content, **kwargs)
        try:
            await self.handler.handle(self, content, **kwargs)
        except defines.ServiceException as e:
            await self.send_error(code=e.code, message=e.message)
        except Exception as e:
            logger.exception(e)
        else:
            await self.post_handle()

    async def post_handle(self, *args, **kwargs):
        pass

    async def pre_handle(self, content, **kwargs):
        pass
