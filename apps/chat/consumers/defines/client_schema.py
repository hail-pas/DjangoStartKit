from typing import Union, Optional, TypedDict

from apps.chat.consumers.defines.chat_type import ChatType
from apps.chat.consumers.defines.message_type import MessageType
from apps.chat.consumers.defines.message_content import (
    FileContent,
    ShareContent,
    UserIdentifier,
    ContentTextType,
    LocationContent,
    MessageIDContent,
)


class MessageSchema(TypedDict):
    chat_type: ChatType
    message_type: MessageType
    receiver_id: Optional[int]
    content: Optional[Union[ContentTextType, FileContent, LocationContent, ShareContent, MessageIDContent,]]
