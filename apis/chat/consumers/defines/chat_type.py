import enum

"""
聊天类型
"""


# @enum.unique
# class ChatTypeUniqueFormatKey(str, enum.Enum):
#     SystemCenter = "SystemCenter"  # 所有的用户在登录的时候连接 用户数量、未读信息、公共推送
#     Group = "Group-%d-%d"  # group_pk - profile_pk
#     Dialog = "Dialog-%d-%d"  # profile_pk-profile_pk


@enum.unique
class ChatType(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group"
    Dialog = "Dialog"


@enum.unique
class ChatTypeContextFormatKey(str, enum.Enum):
    SystemCenter = "SystemCenter"
    Group = "Group-%d"
    # Dialog = "Dialog-%d" # use channel name
