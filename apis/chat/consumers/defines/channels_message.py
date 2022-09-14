import enum
from typing import Literal, TypedDict

from apis.chat.consumers.defines.reply import ServiceReplyData


@enum.unique
class ChannelsMessageType(str, enum.Enum):
    chat_message = "group.message"


ChannelsMessageType_ = Literal[
    ChannelsMessageType.chat_message,
]


class ChannelsMessageData(TypedDict):
    type: Literal["group.message"]
    content: ServiceReplyData
