import enum
from typing import Union, Optional, TypedDict

from apps import enums

# @enum.unique
# class ChatUniqueFormatKey(str, enum.Enum):
#     SystemCenter = "SystemCenter"  # 所有的用户在登录的时候连接 用户数量、未读信息、公共推送
#     Group = "Group-%d-%d"  # group_pk - profile_pk
#     Dialog = "Dialog-%d-%d"  # profile_pk-profile_pk


@enum.unique
class ChatType(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group"
    Dialog = "Dialog"


@enum.unique
class ChatContextFormatKey(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group-%d"
    # Dialog = "Dialog-%d"


@enum.unique
class ClientMessage(str, enum.Enum):
    # 数据信息
    Text = enums.MessageType.text.value
    Picture = enums.MessageType.picture.value
    Video = enums.MessageType.video.value
    Audio = enums.MessageType.audio.value
    Link = enums.MessageType.link.value
    File = enums.MessageType.file.value  # other File
    Location = enums.MessageType.location.value

    # 行为
    Typing = "typing"
    StopTyping = "stop_typing"
    MessageRead = "message_read"


@enum.unique
class MessageType(str, enum.Enum):
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 客户端信息类型
    # 数据信息
    Text = enums.MessageType.text.value
    Picture = enums.MessageType.picture.value
    Video = enums.MessageType.video.value
    Audio = enums.MessageType.audio.value
    Link = enums.MessageType.link.value
    File = enums.MessageType.file.value  # other File
    Location = enums.MessageType.location.value
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # 行为
    Typing = "typing"
    StopTyping = "stop_typing"
    MessageRead = "message_read"

    # 错误
    Error = "error"

    # 事件信息
    Online = "online"
    Offline = "offline"
    Join = "join"

    MessageSent = "message_sent"  # 发送成功回复 message_id 由 chat_instance 和 message_id 唯一组成
    MessageNewUnRead = "message_new_unread"


@enum.unique
class ServiceCode(enum.IntEnum):
    Success = 0

    # 断开连接
    Unauthorized = 40000
    DeviceRestrict = 40001

    # 业务code
    UnSupportedType = 40002
    ReceiverNotExists = 40003
    ValueInvalid = 40005
    InvalidMessageReadId = 40006
    FileDoesNotExist = 40007


@enum.unique
class ServiceMessage(str, enum.Enum):
    Unauthorized = "用户未授权"
    DeviceRestrict = "设备登录限制"

    UnSupportedType = "不支持的%s类型"
    ReceiverNotExists = "接收方不存在"
    ValueInvalid = "消息不符合规范"
    InvalidMessageReadId = "已读消息ID无效"
    FileDoesNotExistFormatter = "文件不存在"


class BaseIdentifierInfo(TypedDict):
    id: str
    avatar: Optional[str]
    nickname: Optional[str]


class SenderInfo(BaseIdentifierInfo):
    pass


class Payload(TypedDict):
    code: Optional[ServiceCode]


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
    chat_type: ChatType
    sender: SenderInfo
    context: str
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


@enum.unique
class DeviceCode(str, enum.Enum):
    mobile = "mobile"
    web = "web"


@enum.unique
class ChannelsMessageType(str, enum.Enum):
    group_message = "group.message"


class ChannelsMessageData(TypedDict):
    type: ChannelsMessageType
    payload: ServiceReplyData


class ServiceException(Exception):
    def __init__(self, code: ServiceCode, message: str):
        self.code = code
        self.message = message


SystemId = "df-lanka"
NickName = "df-lanka"
SystemInfo = SenderInfo(id=SystemId, avatar=None, nickname=NickName)
TextMaxLength = 65535
