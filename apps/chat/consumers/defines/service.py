import enum


@enum.unique
class Code(enum.IntEnum):
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
class Message(str, enum.Enum):
    Unauthorized = "用户未授权"
    DeviceRestrict = "设备登录限制"

    UnSupportedType = "不支持的%s类型"
    ReceiverNotExists = "接收方不存在"
    ValueInvalid = "消息不符合规范"
    InvalidMessageReadId = "已读消息ID无效"
    FileDoesNotExist = "文件不存在"

    # other
    ForbiddenAction = "禁止%s"
