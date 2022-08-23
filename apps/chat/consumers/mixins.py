import logging
from abc import ABC
from typing import Any, Union, Optional
from datetime import datetime

import ujson
from channels.exceptions import StopConsumer
from channels_redis.core import RedisChannelLayer
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.utils import COMMON_TIME_STRING
from storages.redis import AsyncRedisUtil, keys
from apps.chat.models import Group
from apps.account.models import Profile
from apps.chat.consumers import defines
from apps.chat.consumers.decorator import authenticate_required
from apps.chat.consumers.db_operations import get_system_sender, get_group_ids_with_profile_pk

logger = logging.getLogger("chat.consumers.mixins")


class AsyncUJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def decode_json(cls, text_data):
        return ujson.loads(text_data)

    @classmethod
    async def encode_json(cls, content):
        return ujson.dumps(content)

    async def interrupt(self, code: defines.service.Code):
        logger.warning(f"disconnect with code: {code.value}")
        await self.disconnect(code.value)
        raise StopConsumer()

    # to disconnect


class ConnectManageConsumer(AsyncUJsonWebsocketConsumer):
    """
    连接准备工作
    """

    profile: Profile
    device_code: defines.device.DeviceCode
    receiver: Union[Profile, Group, defines.message_content.SenderInfo]
    channel_layer: RedisChannelLayer
    channel_name: str

    @authenticate_required()
    async def pre_accept(self):
        profile = self.scope["user"]
        self.profile = profile
        device_code = self.scope["url_route"]["kwargs"]["device_code"]
        if device_code not in [defines.device.DeviceCode.mobile.value, defines.device.DeviceCode.web.value]:
            logger.warning(f"{profile.id} connect with unknown device_code: {device_code}")
            await self.interrupt(code=defines.service.Code.DeviceRestrict)
        self.device_code = defines.device.DeviceCode(device_code)
        # if await AsyncRedisUtil.r.get(
        #     keys.RedisCacheKey.ProfileConnectionKey.format(profile_id=self.profile.id, device_code=device_code)
        # ):
        #     # 已建立连接
        #     logger.warning(f"{profile.id} connect with duplicate device_code: {device_code}")
        #     await self.interrupt(code=service.Code.DeviceRestrict)

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
            expire=61,
        )
        # 加入系统群组
        await self.channel_layer.group_add(
            defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value, self.channel_name
        )
        # 加入用户的群组
        for group_id in await AsyncRedisUtil.r.smembers(
            keys.RedisCacheKey.ProfileGroupSet.format(profile_id=self.profile.id), encoding="utf-8"
        ):
            await self.channel_layer.group_add(
                defines.chat_type.ChatTypeContextFormatKey.Group.value % int(group_id), self.channel_name
            )
        group_ids = await get_group_ids_with_profile_pk(self.profile.id)
        for group_id in group_ids:
            await self.channel_layer.group_add(
                defines.chat_type.ChatTypeContextFormatKey.Group.value % int(group_id), self.channel_name
            )
        logger.info(f"User {self.profile.id} connected with device_code: {self.device_code}")

    async def connect(self):
        await self.pre_accept()
        await self.accept()
        await self.post_accept()

    async def disconnect(self, close_code):
        if close_code not in [defines.service.Code.Unauthorized.value, defines.service.Code.DeviceRestrict.value]:
            # 用户离线
            logger.info(
                f"User {self.profile.pk} device {self.device_code.value} disconnected, "
                f"removing channel {self.channel_name}"
            )
            # 离开系统群组
            await self.channel_layer.group_discard(
                defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value, self.channel_name
            )

            # 离开用户群组
            for group_id in await AsyncRedisUtil.r.smembers(
                keys.RedisCacheKey.ProfileGroupSet.format(profile_id=self.profile.id), encoding="utf-8"
            ):
                await self.channel_layer.group_discard(
                    defines.chat_type.ChatTypeContextFormatKey.Group.value % int(group_id), self.channel_name
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
    async def group_message(self, message: defines.channels_message.ChannelsMessageData):
        # Send message to WebSocket
        logger.debug(f"message is: {message}")
        await self.send(bytes_data=ujson.dumps(message["content"]).encode())

    @staticmethod
    def gen_reply(
        code: defines.service.Code,
        message_type: defines.message_type.MessageType,
        chat_type: defines.chat_type.ChatType,
        sender_info: defines.message_content.SenderInfo,
        context: str,
        time: datetime,
        content=None,
    ):
        reply_data = defines.reply.ServiceReplyData(
            code=code.value,  # noqa
            message_type=message_type.value,
            chat_type=chat_type.value,
            sender=sender_info,
            context=context,
            time=time.strftime(COMMON_TIME_STRING),
            content=content,
        )
        logger.debug(f"reply data is: {reply_data}")
        return reply_data

    def gen_reply_bytes(
        self,
        code: defines.service.Code,
        message_type: defines.message_type.MessageType,
        chat_type: defines.chat_type.ChatType,
        sender_info: defines.message_content.SenderInfo,
        context: str,
        time: datetime,
        content: Any = None,
    ):
        return ujson.dumps(self.gen_reply(code, message_type, chat_type, sender_info, context, time, content)).encode()

    async def send_error(self, code: defines.service.Code, message: Optional[str]):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=code,
                message_type=defines.message_type.MessageType.Error,
                chat_type=defines.chat_type.ChatType.SystemCenter,
                sender_info=await get_system_sender(),
                context=defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value,
                time=datetime.now(),
                content=message,
            )
        )

    async def gen_sender_info(self, is_system: bool = False) -> defines.message_content.SenderInfo:
        if is_system:
            return await get_system_sender()
        avatar = None
        # 数据库的信息更新不会同步到 consumer 中的 profile
        # 不缓存直接获取 或者 使用 redis
        if self.profile.avatar:
            avatar = self.profile.avatar.url
        return defines.message_content.SenderInfo(
            id=str(self.profile.id), avatar=avatar, nickname=self.profile.nickname
        )

    async def send_text(
        self,
        chat_type: defines.chat_type.ChatType,
        sender_info: defines.message_content.SenderInfo,
        context: str,
        time: datetime,
        content: Any = None,
    ):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=defines.service.Code.Success,
                message_type=defines.message_type.MessageType.Text,
                chat_type=chat_type,
                sender_info=sender_info,
                context=context,
                time=time,
                content=content,
            )
        )

    async def send_file(
        self,
        message_type: defines.message_type.MessageType,
        chat_type: defines.chat_type.ChatType,
        sender_info: defines.message_content.SenderInfo,
        context: str,
        time: datetime,
        id_: int,
        url: str,
        label: Optional[str],
        size: int,
        extension: str,
    ):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=defines.service.Code.Success,
                message_type=message_type,
                chat_type=chat_type,
                sender_info=sender_info,
                context=context,
                time=time,
                content=defines.message_content.FileContent(
                    id=id_, url=url, label=label, size=size, extension=extension
                ),
            )
        )

    async def send_event_message(self, message_type: defines.message_type.MessageType):
        """
        Online、Offline、Join、Typing、StopTyping
        """
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=defines.service.Code.Success,
                message_type=message_type,
                chat_type=defines.chat_type.ChatType.SystemCenter,
                sender_info=await get_system_sender(),
                context=defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value,
                time=datetime.now(),
            )
        )

    async def send_message_status(
        self,
        message_type: defines.message_type.MessageType,
        user_info: defines.message_content.UserIdentifier,
        chat_instance_id: int,
        message_id: int,
    ):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=defines.service.Code.Success,
                message_type=message_type,
                chat_type=defines.chat_type.ChatType.SystemCenter,
                sender_info=await get_system_sender(),
                context=defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value,
                time=datetime.now(),
                content=defines.message_content.MessageIDContent(
                    user_info=user_info, chat_instance_id=chat_instance_id, message_id=message_id
                ),
            )
        )

    async def send_message_unread_count(self, chat_instance_id: int, message_id: int, count: int):
        await self.send(
            bytes_data=self.gen_reply_bytes(
                code=defines.service.Code.Success,
                message_type=defines.message_type.MessageType.MessageNewUnRead,
                chat_type=defines.chat_type.ChatType.SystemCenter,
                sender_info=await get_system_sender(),
                context=defines.chat_type.ChatTypeContextFormatKey.SystemCenter.value,
                time=datetime.now(),
                content=defines.message_content.MessageUnreadCount(
                    chat_instance_id=chat_instance_id, message_id=message_id, count=count
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
        except defines.exceptions.ServiceException as e:
            await self.send_error(code=e.code, message=e.message)
        except Exception as e:
            logger.exception(e)
        else:
            await self.post_handle()

    async def post_handle(self, *args, **kwargs):
        pass

    async def pre_handle(self, content, **kwargs):
        pass
