import enum
from typing import Union, Optional, TypedDict

from apps import enums


@enum.unique
class ChatUniqueFormatKey(str, enum.Enum):
    SystemCenter = "SystemCenter"  # 所有的用户在登录的时候连接 用户数量、未读信息、公共推送
    Group = "Group-%d-%d"  # group_pk - profile_pk
    Dialog = "Dialog-%d-%d"  # profile_pk-profile_pk


@enum.unique
class ChatType(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group"
    Dialog = "Dialog"


@enum.unique
class RoomNameUniqueFormatKey(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group-%d"
    Dialog = "Dialog-%d"


@enum.unique
class MessageType(str, enum.Enum):
    # 错误
    Error = "error"

    # 数据信息
    Text = enums.MessageType.text.value
    Picture = enums.MessageType.picture.value
    Video = enums.MessageType.video.value
    Audio = enums.MessageType.audio.value
    Link = enums.MessageType.link.value
    File = enums.MessageType.file.value  # other File
    Location = enums.MessageType.location.value

    # 事件信息
    Online = "online"
    Offline = "offline"
    Join = "join"

    Typing = "typing"
    StopTyping = "stopTyping"

    MessageRead = "messageRead"
    MessageSent = "messageSent"  # 发送成功回复
    MessageNewUnRead = "messageNewUnRead"


@enum.unique
class ServiceCode(enum.IntEnum):
    Success = 0

    # 断开连接
    UnSupportedChatType = 40000
    Unauthorized = 40001

    # 业务code
    ReceiverNotExists = 40002
    MessageParsingError = 40003
    TextMessageInvalid = 40004
    InvalidMessageReadId = 40005
    FileDoesNotExist = 40006


@enum.unique
class ServiceMessage(str, enum.Enum):
    Unauthorized = "用户未授权"
    ReceiverNotExists = "接收方不存在"
    MessageParsingError = "消息解析失败"
    TextMessageInvalid = "消息不符合规范"
    InvalidMessageReadId = "已读消息ID无效"
    FileDoesNotExistFormatter = "%s不存在"


@enum.unique
class SenderType(str, enum.Enum):
    system = "system"
    user = "user"


class BaseIdentifierInfo(TypedDict):
    id: str
    avatar: Optional[str]
    nickname: Optional[str]


class SenderInfo(BaseIdentifierInfo):
    type: SenderType


class Payload(TypedDict):
    code: ServiceCode
    sender: SenderInfo


class PayloadMessageNewUnRead(Payload):
    connection_info: "ConnectionInfo"
    count: int
    message_id: int


class PayloadMessageSent(Payload):
    message_id: int


class PayloadMessageRead(Payload):
    user_info: BaseIdentifierInfo
    message_id: int


class PayloadStopTyping(Payload):
    user_info: BaseIdentifierInfo


class PayloadTyping(Payload):
    user_info: BaseIdentifierInfo


class PayloadJoin(Payload):
    user_info: BaseIdentifierInfo


class PayloadOffline(Payload):
    user_info: BaseIdentifierInfo


class PayloadOnline(Payload):
    user_info: BaseIdentifierInfo


class PayloadError(Payload):
    message: Optional[str]


class PayloadText(Payload):
    value: str


class PayLoadFile(Payload):
    """
    picture、video、audio、file
    """

    id: int
    url: str
    name: str
    size: int
    extension: str


class PayloadLocation(Payload):
    longitude: float
    latitude: float


class ConnectionInfo(TypedDict):
    chat_type: ChatType
    chat_unique_id: str
    channel_name: str


class ServiceReplyData(TypedDict):
    type: MessageType
    payload: Optional[
        Union[
            Payload,
            PayloadError,
            PayloadLocation,
            PayloadText,
            PayloadOnline,
            PayloadOffline,
            PayloadJoin,
            PayloadTyping,
            PayloadStopTyping,
            PayLoadFile,
            PayloadMessageSent,
            PayloadMessageRead,
            PayloadMessageNewUnRead,
        ]
    ]
    connection_info: ConnectionInfo


class ServiceException(Exception):
    def __init__(self, service_code: ServiceCode, message: str):
        self.code = service_code
        self.message = message

    def payload_error(self):
        return PayloadError(code=self.code, message=self.message)


SystemId = "df-lanka"
NickName = "df-lanka"
SystemInfo = SenderInfo(type=SenderType.system, id=SystemId, avatar=None, nickname=NickName)
TextMaxLength = 65535
