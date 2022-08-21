import logging
from typing import Set

from storages.redis import AsyncRedisUtil, keys
from apps.chat.models import UploadedFile
from apps.chat.consumers.mixins import ServerReply
from apps.chat.consumers.defines import (
    device,
    service,
    chat_type,
    exceptions,
    message_type,
    client_schema,
    channels_message,
)
from apps.chat.consumers.db_operations import get_receiver, save_message, get_chat_instance, get_user_file_with_pk

logger = logging.getLogger("chat.consumer.handler")


class BaseHandler:
    """
    处理 和 转发
    """

    support_chat_type: Set = {i.value for i in chat_type.ChatType}
    support_message_type: Set = {i.value for i in message_type.ClientMessageType}

    async def handle(self, consumer: ServerReply, content: client_schema.MessageSchema, **kwargs):

        current_chat_type = content.get("chat_type")
        # chatType校验
        if current_chat_type not in self.support_chat_type:
            logger.warning(f"UnSupported chat type: {current_chat_type}")
            raise exceptions.ServiceException(
                code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "chatType"
            )
        current_chat_type = chat_type.ChatType(current_chat_type)
        # messageType 校验
        current_message_type = content.get("message_type")
        if current_message_type not in self.support_message_type:
            logger.warning(f"UnSupported message type: {current_message_type}")
            raise exceptions.ServiceException(
                code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "messageType"
            )
        current_message_type = message_type.MessageType(current_message_type)

        # 接收者校验
        receiver_id = content.get("receiver_id")
        if current_chat_type == current_chat_type.ChatType.SystemCenter:
            chat_instance_id = None
            related_id = None
        else:
            chat_instance = await get_chat_instance(current_chat_type, consumer.profile.pk, receiver_id)
            if not chat_instance:
                logger.warning(f"Receiver doesnt exists: {current_chat_type}")
                raise exceptions.ServiceException(
                    code=service.Code.ReceiverNotExists, message=service.Message.ReceiverNotExists
                )
            chat_instance_id = chat_instance.id
            receiver = await get_receiver(current_chat_type, receiver_id)
            if current_chat_type == current_chat_type.ChatType.Dialog:
                if receiver_id == consumer.profile.id:
                    logger.warning(f"Receiver doesnt exists: {current_chat_type}")
                    raise exceptions.ServiceException(
                        code=service.Code.UnSupportedType, message=service.Message.ForbiddenAction % "给自己发送消息"
                    )
            related_id = receiver.id
        message_handler = getattr(self, f"handle_{current_message_type.value}")
        if not message_handler:
            logger.warning(f"No handler for message type: {current_message_type.value}")
            raise exceptions.ServiceException(
                code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "消息"
            )
        value = content.get("content")
        if not value:
            logger.warning(f"client send empty content")
            raise exceptions.ServiceException(
                code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "消息"
            )
        await message_handler(
            current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
        )

    @staticmethod
    async def save_and_transfer(
        current_chat_type, current_message_type, value, consumer: ServerReply, chat_instance_id, related_id, **kwargs
    ):
        message = await save_message(
            chat_type=current_chat_type,
            profile_id=consumer.profile.id,
            related_id=related_id,
            message_type=current_message_type,
            value=value,
        )
        await consumer.send_message_status(
            message_type=current_message_type.MessageType.MessageSent,
            user_info=await consumer.gen_sender_info(),
            chat_instance_id=chat_instance_id,
            message_id=message.id,
        )
        if current_chat_type == current_chat_type.ChatType.Group:
            await consumer.channel_layer.group_send(
                current_chat_type.ChatContextFormatKey.Group.value % related_id,
                channels_message.ChannelsMessageData(
                    type="group.message",
                    content=consumer.gen_reply(
                        code=service.Code.Success,
                        message_type=current_message_type,
                        chat_type=current_chat_type,
                        sender_info=await consumer.gen_sender_info(),
                        context=current_chat_type.ChatContextFormatKey.Group.value % related_id,
                        time=message.create_time,
                        content=value,
                    ),
                ),
            )
        elif current_chat_type == current_chat_type.ChatType.Dialog:
            for device_code in device.DeviceCode:
                channel_name = await AsyncRedisUtil.r.get(
                    keys.RedisCacheKey.ProfileConnectionKey.format(
                        profile_id=related_id, device_code=device_code.value
                    ),
                    encoding="utf-8",
                )
                if channel_name:
                    await consumer.channel_layer.send(
                        channel_name,
                        channels_message.ChannelsMessageData(
                            type="group.message",
                            content=consumer.gen_reply(
                                code=service.Code.Success,
                                message_type=current_message_type,
                                chat_type=current_chat_type,
                                sender_info=await consumer.gen_sender_info(),
                                context=channel_name,
                                time=message.create_time,
                                content=value,
                            ),
                        ),
                    )
        else:
            raise exceptions.ServiceException(
                code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "持久化信息类型"
            )

    async def handle_text(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in current_chat_type.ChatType:
            await self.save_and_transfer(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
            )
        else:
            # system 处理
            pass

    async def handle_location(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in current_chat_type.ChatType:
            await self.save_and_transfer(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
            )
        else:
            # system 处理
            pass

    async def handle_file(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        if current_chat_type in current_chat_type.ChatType:
            try:
                file_id = int(value["id"])
            except Exception:
                raise exceptions.ServiceException(
                    code=service.Code.UnSupportedType, message=service.Message.UnSupportedType % "content"
                )

            file_instance: UploadedFile = await get_user_file_with_pk(consumer.profile.id, file_id)
            if not file_instance or file_instance.size <= 0:
                raise exceptions.ServiceException(
                    code=service.eCode.FileDoesNotExist, message=service.Message.FileDoesNotExist
                )
            await self.save_and_transfer(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
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
        if current_chat_type in chat_type.ChatType:
            await self.save_and_transfer(
                current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
            )
        else:
            # system 处理
            pass

    async def handle_typing(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        # if current_chat_type == chat_type.ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass

    async def handle_stop_typing(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        # if current_chat_type == ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass

    async def handle_message_read(
        self, current_chat_type, current_message_type, value, consumer, chat_instance_id, related_id, **kwargs
    ):
        # if current_chat_type == ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass
