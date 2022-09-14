import enum


@enum.unique
class Code(enum.IntEnum):
    Success = 0

    # 断开连接
    Unauthorized = 40000
    DeviceRestrict = 40001

    # 业务code
    UnSupportedType = 40002
    RelationShipNotExists = 40003
    ReceiverNotExists = 40004
    FileDoesNotExist = 40005

    # other
    ForbiddenAction = 50000


@enum.unique
class Message(str, enum.Enum):
    Unauthorized = "用户未授权"
    DeviceRestrict = "设备登录限制"

    UnSupportedType = "不支持的%s类型"
    RelationShipNotExists = "%s关系未建立，无法发送消息"
    ReceiverNotExists = "接收方不存在"
    FileDoesNotExist = "文件不存在"

    # other
    ForbiddenAction = "禁止%s"
