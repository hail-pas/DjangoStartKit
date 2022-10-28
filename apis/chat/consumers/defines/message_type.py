import enum
from typing import NewType

from storages import enums
from common.decorators import extend_enum

"""
消息类型
"""


@enum.unique
class ClientMessageType(str, enum.Enum):
    # 数据信息
    Text = enums.MessageType.text.value  # 文本
    Picture = enums.MessageType.picture.value  # 图片
    Video = enums.MessageType.video.value  # 视频、包含封面
    Audio = enums.MessageType.audio.value  # 音频
    File = enums.MessageType.file.value  # 其他文件
    # Link = enums.MessageType.link.value  # 链接
    Location = enums.MessageType.location.value  # 定位
    Share = enums.MessageType.share.value  # 分享

    # 行为
    Typing = "typing"
    StopTyping = "stop_typing"
    MessageRead = "message_read"


class TextTag(str, enum.Enum):
    title = "title"
    text = "text"
    link = "link"
    at = "at"
    image = "image"
    emoji = "emoji"


TextTagType = NewType("TextTag", TextTag)


@enum.unique
class ServerOnlyMessageType(str, enum.Enum):
    # 错误
    Error = "error"

    # 事件信息
    Online = "online"
    Offline = "offline"
    Join = "join"

    MessageSent = "message_sent"  # 发送成功回复 message_id 由 chat_instance 和 message_id 唯一组成
    MessageNewUnRead = "message_new_unread"


@enum.unique
@extend_enum(ClientMessageType, ServerOnlyMessageType)
class MessageType(str, enum.Enum):
    pass
