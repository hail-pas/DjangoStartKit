from typing import List, Union, NewType, Optional, TypedDict

from apps.chat.consumers.defines.chat_type import ChatType
from apps.chat.consumers.defines.message_type import TextTagType


class UserIdentifier(TypedDict):
    id: str
    avatar: Optional[str]
    nickname: Optional[str]


class SenderInfo(UserIdentifier):
    pass


class TextTitleContent(TypedDict):
    tag: TextTagType
    value: str


class TextTextContent(TypedDict):
    tag: TextTagType
    value: str


class TextLinkContent(TypedDict):
    tag: TextTagType
    value: str
    label: Optional[str]


class TextAtContent(TypedDict):
    tag: TextTagType
    value: UserIdentifier


class TextImageContent(TypedDict):
    tag: TextTagType
    value: str


class TextEmojiContent(TypedDict):
    tag: TextTagType
    value: str


ContentTextType = List[
    Union[TextTitleContent, TextTextContent, TextLinkContent, TextAtContent, TextImageContent, TextEmojiContent]
]


class FileContent(TypedDict):
    id: int
    url: str
    label: Optional[str]
    size: int
    extension: str


class LocationContent(TypedDict):
    longitude: float
    latitude: float


class MessageIdentifier(TypedDict):
    message_id: int


class MessageIDContent(MessageIdentifier):
    user_info: UserIdentifier


class ShareContent(UserIdentifier):
    share_type: ChatType


class MessageUnreadCount(MessageIdentifier):
    count: int
