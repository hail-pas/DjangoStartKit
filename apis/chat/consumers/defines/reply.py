from typing import Union, Optional, TypedDict

from apis.chat.consumers.defines.service import Code
from apis.chat.consumers.defines.chat_type import ChatType
from apis.chat.consumers.defines.message_type import MessageType
from apis.chat.consumers.defines.message_content import (
    SenderInfo,
    FileContent,
    ShareContent,
    ContentTextType,
    LocationContent,
    MessageIDContent,
    MessageUnreadCount,
)


class ServiceReplyData(TypedDict):
    code: Code
    message_type: MessageType
    chat_type: ChatType
    sender: SenderInfo
    context: str
    time: str
    content: Optional[
        Union[str, ContentTextType, FileContent, LocationContent, ShareContent, MessageIDContent, MessageUnreadCount]
    ]
