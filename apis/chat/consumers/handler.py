import logging
import datetime
from typing import Set, Optional

import storages.mysql.models.chat
from storages.redis import AsyncRedisUtil, keys
from apis.chat.consumers import defines
from storages.mysql.models import UploadedFile
from apis.chat.consumers.mixins import ServerReply
from apis.chat.consumers.db_operations import (
    get_receiver,
    save_message,
    get_chat_instance,
    get_user_file_with_pk,
    update_unread_messages,
)

logger = logging.getLogger("chat.consumers.handler")


class BaseHandler:
    """
    处理 和 转发
    """

    support_chat_type: Set = {i.value for i in defines.chat_type.ChatType}
    support_message_type: Set = {i.value for i in defines.message_type.ClientMessageType}

    async def handle(self, consumer: ServerReply, content: defines.client_schema.MessageSchema, **kwargs):

        current_chat_type = content.get("chat_type")
        # chatType校验
        if current_chat_type not in self.support_chat_type:
            logger.warning(f"UnSupported chat type: {current_chat_type}")
            raise defines.exceptions.ServiceException(
                code=defines.service.Code.UnSupportedType, message=defines.service.Message.UnSupportedType % "chatType"
            )
        current_chat_type = defines.chat_type.ChatType(current_chat_type)
        # messageType 校验
        current_message_type = content.get("message_type")
        if current_message_type not in self.support_message_type:
            logger.warning(f"UnSupported message type: {current_message_type}")
            raise defines.exceptions.ServiceException(
                code=defines.service.Code.UnSupportedType,
                message=defines.service.Message.UnSupportedType % "messageType",
            )
        current_message_type = defines.message_type.MessageType(current_message_type)

        # 接收者校验
        receiver_id = content.get("receiver_id")
        if current_chat_type == defines.chat_type.ChatType.SystemCenter:
            chat_instance_id = None
            related_id = None
        else:
            chat_instance = await get_chat_instance(current_chat_type, consumer.profile.pk, receiver_id)
            if not chat_instance:
                logger.warning(f"Relation doesnt exists: {current_chat_type}-{consumer.profile.pk}-{receiver_id}")
                raise defines.exceptions.ServiceException(
                    code=defines.service.Code.RelationShipNotExists,
                    message=defines.service.Message.RelationShipNotExists,
                )
            chat_instance_id = chat_instance.id
            receiver = await get_receiver(current_chat_type, receiver_id)
            if current_chat_type == defines.chat_type.ChatType.Dialog:
                if receiver_id == consumer.profile.id:
                    logger.warning(f"Forbidden action: send to self")
                    raise defines.exceptions.ServiceException(
                        code=defines.service.Code.ForbiddenAction,
                        message=defines.service.Message.ForbiddenAction % "给自己发送消息",
                    )
            related_id = receiver.id
        message_handler = getattr(self, f"handle_{current_message_type.value}")
        if not message_handler:
            logger.warning(f"No handler for message type: {current_message_type.value}")
            raise defines.exceptions.ServiceException(
                code=defines.service.Code.UnSupportedType, message=defines.service.Message.UnSupportedType % "消息"
            )
        value = content.get("content")
        if not value:
            logger.warning(f"client send empty content")
            raise defines.exceptions.ServiceException(
                code=defines.service.Code.UnSupportedType, message=defines.service.Message.UnSupportedType % "消息"
            )
        await message_handler(
            current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
        )

    @staticmethod
    async def transfer_message(
        current_chat_type, current_message_type, value, consumer: ServerReply, related_id, **kwargs
    ):
        if current_chat_type == defines.chat_type.ChatType.Group:
            await consumer.channel_layer.group_send(
                defines.chat_type.ChatTypeContextFormatKey.Group.value % related_id,
                defines.channels_message.ChannelsMessageData(
                    type="group.message",
                    content=consumer.gen_reply(
                        code=defines.service.Code.Success,
                        message_type=current_message_type,
                        chat_type=current_chat_type,
                        sender_info=await consumer.gen_sender_info(),
                        context=defines.chat_type.ChatTypeContextFormatKey.Group.value % related_id,
                        time=kwargs["message_time"],
                        content=value,
                    ),
                ),
            )
        elif current_chat_type == defines.chat_type.ChatType.Dialog:
            for device_code in defines.device.DeviceCode:
                channel_name = await AsyncRedisUtil.r.get(
                    keys.RedisCacheKey.ProfileConnectionKey.format(
                        profile_id=related_id, device_code=device_code.value
                    ),
                    encoding="utf-8",
                )
                if channel_name:
                    await consumer.channel_layer.send(
                        channel_name,
                        defines.channels_message.ChannelsMessageData(
                            type="group.message",
                            content=consumer.gen_reply(
                                code=defines.service.Code.Success,
                                message_type=current_message_type,
                                chat_type=current_chat_type,
                                sender_info=await consumer.gen_sender_info(),
                                context=channel_name,
                                time=kwargs["message_time"],
                                content=value,
                            ),
                        ),
                    )
        else:
            raise defines.exceptions.ServiceException(
                code=defines.service.Code.UnSupportedType, message=defines.service.Message.UnSupportedType % "持久化信息类型"
            )

    @staticmethod
    async def save_message(
        current_chat_type, current_message_type, value, consumer: ServerReply, chat_instance_id, related_id,
    ):
        message = await save_message(
            chat_type=current_chat_type,
            profile_id=consumer.profile.id,
            related_id=related_id,
            message_type=current_message_type,
            value=value,
            dialog_id=chat_instance_id,
        )
        await consumer.send_message_status(
            message_type=defines.message_type.MessageType.MessageSent,
            user_info=await consumer.gen_sender_info(),
            chat_instance_id=chat_instance_id,
            message_id=message.id,
        )
        return message

    async def handle_text(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in [defines.chat_type.ChatType.Group, defines.chat_type.ChatType.Dialog]:
            message = await self.save_message(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id
            )
            await self.transfer_message(
                current_chat_type, current_message_type, value, consumer, related_id, message_time=message.create_time
            )
        else:
            # system 处理
            pass

    async def handle_location(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in [defines.chat_type.ChatType.Group, defines.chat_type.ChatType.Dialog]:
            message = await self.save_message(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id
            )
            await self.transfer_message(
                current_chat_type, current_message_type, value, consumer, related_id, message_time=message.create_time
            )
        else:
            # system 处理
            pass

    async def handle_file(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in [defines.chat_type.ChatType.Group, defines.chat_type.ChatType.Dialog]:
            try:
                file_id = int(value["id"])
            except Exception:
                raise defines.exceptions.ServiceException(
                    code=defines.service.Code.UnSupportedType,
                    message=defines.service.Message.UnSupportedType % "content",
                )

            file_instance: UploadedFile = await get_user_file_with_pk(consumer.profile.id, file_id)
            if not file_instance or file_instance.size <= 0:
                raise defines.exceptions.ServiceException(
                    code=defines.service.Code.FileDoesNotExist, message=defines.service.Message.FileDoesNotExist
                )
            message = await self.save_message(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id
            )
            await self.transfer_message(
                current_chat_type, current_message_type, value, consumer, related_id, message_time=message.create_time
            )
        else:
            # system 处理
            pass

    async def handle_picture(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        await self.handle_file(
            current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
        )

    async def handle_video(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        await self.handle_file(
            current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
        )

    async def handle_audio(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        await self.handle_file(
            current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
        )

    async def handle_share(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in [defines.chat_type.ChatType.Group, defines.chat_type.ChatType.Dialog]:
            message = await self.save_message(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id
            )
            await self.transfer_message(
                current_chat_type, current_message_type, value, consumer, related_id, message_time=message.create_time
            )
        else:
            # system 处理
            pass

    async def _handle_action(self):
        pass

    async def handle_typing(
        self, current_chat_type, current_message_type, value: Optional, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type == defines.chat_type.ChatType.Dialog:
            """
            只有私聊的时候才有 typing 和 stop_typing
            """
            await self.transfer_message(
                current_chat_type,
                current_message_type,
                value,
                consumer,
                related_id,
                message_time=datetime.datetime.now(),
            )
        else:
            # 非系统类型
            pass

    async def handle_stop_typing(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type == defines.chat_type.ChatType.Dialog:
            """
            只有私聊的时候才有 typing 和 stop_typing
            """
            await self.transfer_message(
                current_chat_type,
                current_message_type,
                value,
                consumer,
                related_id,
                message_time=datetime.datetime.now(),
            )
        else:
            # 非系统类型
            pass

    async def handle_message_read(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type == defines.chat_type.ChatType.Dialog:
            """
            私聊已读
            """
            await update_unread_messages(chat_instance_id, consumer.profile.id, value["message_id"])
            await self.transfer_message(
                current_chat_type,
                current_message_type,
                value,
                consumer,
                related_id,
                message_time=datetime.datetime.now(),
            )
        elif current_chat_type == defines.chat_type.ChatType.Group:
            """
            群聊已读
            """
            pass
        else:
            # 非系统类型
            pass
