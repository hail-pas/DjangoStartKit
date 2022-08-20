import logging
from typing import Set, Union

from storages.redis import AsyncRedisUtil, keys
from apps.chat.models import Group, Dialog, UploadedFile, GroupMembership
from apps.chat.consumers import defines
from apps.chat.consumers.mixins import ServerReply
from apps.chat.consumers.db_operations import (
    get_receiver,
    get_chat_instance,
    save_group_message,
    save_dialog_message,
    get_user_file_with_pk,
)

logger = logging.getLogger("chat.consumer.handler")


class BaseHandler:
    """
    处理 和 转发
    """

    support_chat_type: Set = {i.value for i in defines.ChatType}
    support_message_type: Set = {i.value for i in defines.ClientMessage}

    async def handle(self, consumer: ServerReply, content: dict, **kwargs):

        chat_type = content.get("chat_type")
        # chatType校验
        if chat_type not in self.support_chat_type:
            await consumer.send_error(
                code=defines.ServiceCode.UnSupportedType, message=defines.ServiceMessage.UnSupportedType % "chatType"
            )
            logger.warning(f"UnSupported chat type: {chat_type}")
            return
        chat_type = defines.ChatType(chat_type)
        # messageType 校验
        message_type = content.get("type")
        if message_type not in self.support_message_type:
            await consumer.send_error(
                code=defines.ServiceCode.UnSupportedType, message=defines.ServiceMessage.UnSupportedType % "messageType"
            )
            logger.warning(f"UnSupported message type: {message_type}")
            return
        message_type = defines.MessageType(message_type)

        # 接收者校验
        receiver_id = content.get("receiver_id")
        if chat_type == defines.ChatType.SystemCenter:
            receiver = defines.SystemInfo
        else:
            chat_instance = await get_chat_instance(chat_type, consumer.profile.pk, receiver_id)
            if not chat_instance:
                await consumer.send_error(
                    code=defines.ServiceCode.ReceiverNotExists, message=defines.ServiceMessage.ReceiverNotExists
                )
                logger.warning(f"Receiver doesnt exists: {chat_type}")
                return
            receiver = await get_receiver(chat_type, receiver_id)
            if chat_type == defines.ChatType.Dialog:
                if receiver_id == consumer.profile.id:
                    await consumer.send_error(code=defines.ServiceCode.UnSupportedType, message="不支持自己给自己发送消息")
                    logger.warning(f"Receiver doesnt exists: {chat_type}")
                    return

        await getattr(self, f"handle_{message_type.value}")(consumer, chat_type, receiver, content, **kwargs)

    @staticmethod
    async def group_save_and_send(consumer, receiver: Group, chat_type, message_type, value, payload, file_id=None):
        message = await save_group_message(
            group_id=receiver.id,
            profile_id=consumer.profile.id,
            type_=message_type.value,
            value=value,
            file_id=file_id,
        )
        await consumer.channel_layer.group_send(
            defines.ChatContextFormatKey.Group.value % receiver.id,
            {
                "type": "group.message",
                "payload": consumer.gen_reply(
                    context=defines.ChatContextFormatKey.Group.value % receiver.id,
                    chat_type=chat_type.value,
                    sender_info=consumer.gen_sender_info(),
                    type_=message_type.value,
                    payload=payload,
                ),
            },
        )
        await consumer.send_message_sent(message_id=message.id)

    @staticmethod
    async def dialog_save_and_send(consumer, receiver_id, chat_type, message_type, value, payload, file_id=None):
        message = await save_dialog_message(
            sender_id=consumer.profile.id,
            receiver_id=receiver_id,
            type_=message_type.value,
            value=value,
            file_id=file_id,
        )
        for device_code in defines.DeviceCode:
            channel_name = await AsyncRedisUtil.r.get(
                keys.RedisCacheKey.ProfileConnectionKey.format(profile_id=receiver_id, device_code=device_code.value),
                encoding="utf-8",
            )
            if channel_name:
                await consumer.channel_layer.send(
                    channel_name,
                    {
                        "type": "group.message",
                        "payload": consumer.gen_reply(
                            context=channel_name,
                            chat_type=chat_type.value,
                            sender_info=consumer.gen_sender_info(),
                            type_=message_type.value,
                            payload=payload,
                        ),
                    },
                )

        await consumer.send_message_sent(message_id=message.id)

    async def payload_value_handle(
        self,
        consumer: ServerReply,
        chat_type: defines.ChatType,
        receiver: Union[Dialog, Group],
        message_type,
        content: dict,
        **kwargs,
    ):
        try:
            value = content["payload"]["value"]
        except Exception:
            raise defines.ServiceException(
                code=defines.ServiceCode.UnSupportedType, message=defines.ServiceMessage.UnSupportedType % "payload"
            )
        if not value:
            raise defines.ServiceException(
                code=defines.ServiceCode.ValueInvalid, message=defines.ServiceMessage.ValueInvalid
            )
        payload = defines.PayloadText(code=defines.ServiceCode.Success.value, value=value)
        if chat_type == defines.ChatType.Group:
            await self.group_save_and_send(consumer, receiver, chat_type, message_type, value, payload=payload)
        elif chat_type == defines.ChatType.Dialog:
            await self.dialog_save_and_send(
                consumer, content["receiver_id"], chat_type, message_type, value, payload=payload
            )
        else:
            # 主动发给系统的信息当前没有定义
            pass

    async def handle_text(self, consumer: ServerReply, chat_type: defines.ChatType, receiver, content: dict, **kwargs):
        await self.payload_value_handle(consumer, chat_type, receiver, defines.MessageType.Text, content, **kwargs)

    async def handle_link(self, consumer: ServerReply, chat_type: defines.ChatType, receiver, content: dict, **kwargs):
        await self.payload_value_handle(consumer, chat_type, receiver, defines.MessageType.Link, content, **kwargs)

    async def handle_location(
        self, consumer: ServerReply, chat_type: defines.ChatType, receiver, content: dict, **kwargs
    ):
        try:
            longitude = float(content["payload"]["longitude"])
            latitude = float(content["payload"]["latitude"])
        except Exception:
            raise defines.ServiceException(
                code=defines.ServiceCode.UnSupportedType, message=defines.ServiceMessage.UnSupportedType % "payload"
            )
        payload = defines.PayloadLocation(
            code=defines.ServiceCode.Success.value, longitude=longitude, latitude=latitude
        )
        if chat_type == defines.ChatType.Group:
            await self.group_save_and_send(
                consumer,
                receiver,
                chat_type,
                defines.MessageType.Location,
                value=f"{longitude},{latitude}",
                payload=payload,
            )
        elif chat_type == defines.ChatType.Dialog:
            await self.dialog_save_and_send(
                consumer,
                content["receiver_id"],
                chat_type,
                defines.MessageType.Location,
                value=f"{longitude},{latitude}",
                payload=payload,
            )
        else:
            # 主动发给系统的信息当前没有定义
            pass

    async def handle_typing(self, consumer, chat_type, receiver, content, **kwargs):
        # if chat_type == defines.ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass

    async def handle_stop_typing(self, consumer, chat_type, receiver, content, **kwargs):
        # if chat_type == defines.ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass

    async def handle_message_read(self, consumer, chat_type, receiver, content, **kwargs):
        # if chat_type == defines.ChatType.SystemCenter:
        #     pass
        # else:
        #     # 非系统类型
        #     pass
        pass

    async def handle_file(
        self, consumer, chat_type, receiver, content, message_type=defines.MessageType.File, **kwargs
    ):
        try:
            file_id = int(content["payload"]["id"])
        except Exception:
            raise defines.ServiceException(
                code=defines.ServiceCode.UnSupportedType, message=defines.ServiceMessage.UnSupportedType % "payload"
            )

        file_instance: UploadedFile = await get_user_file_with_pk(consumer.profile.id, file_id)
        if not file_instance or file_instance.size <= 0:
            raise defines.ServiceException(
                code=defines.ServiceCode.FileDoesNotExist, message=defines.ServiceMessage.FileDoesNotExistFormatter
            )

        value = file_instance.file.url
        payload = defines.PayLoadFile(
            code=defines.ServiceCode.Success.value,
            id=file_id,
            url=value,
            name=file_instance.name,
            size=file_instance.size,
            extension=file_instance.extension,
        )

        if chat_type == defines.ChatType.Group:
            await self.group_save_and_send(consumer, receiver, chat_type, message_type, value, file_id, payload)
        elif chat_type == defines.ChatType.Dialog:
            await self.dialog_save_and_send(
                consumer, content["receiver_id"], chat_type, message_type, value, file_id, payload
            )
        else:
            # 主动发给系统的信息当前没有定义
            pass

    async def handle_picture(self, consumer, chat_type, receiver, content, **kwargs):
        await self.handle_file(consumer, chat_type, receiver, content, defines.MessageType.Picture)

    async def handle_video(self, consumer, chat_type, receiver, content, **kwargs):
        await self.handle_file(consumer, chat_type, receiver, content, defines.MessageType.Video)

    async def handle_audio(self, consumer, chat_type, receiver, content, **kwargs):
        await self.handle_file(consumer, chat_type, receiver, content, defines.MessageType.Audio)
