"""
全部的Enum类型
"""
import sys
import inspect
from enum import unique
from typing import List, Tuple

from common.types import MyEnum, IntEnumMore, StrEnumMore


@unique
class ResponseCodeEnum(IntEnumMore):
    """
    业务响应代码，除了500之外都在200的前提下返回对用code
    """

    # 唯一成功响应
    success = (0, "成功")

    # HTTP 状态码  2xx - 5xx
    # 100{[2-5]]xx}, http status code 拼接

    # 失败响应，999倒序取
    failed = (200001, "失败")


# class EnumInfoResponseFormats(StrEnumMore):
#     """
#     码表信息响应格式
#     """
#     json_ = ("json", "Json")
#     list_ = ("list", "数组")


class SystemResourceTypeEnum(StrEnumMore):
    """
    系统资源
    """

    menu = ("menu", "菜单")
    button = ("button", "按钮")
    api = ("api", "接口")


class PermissionRelationEnum(StrEnumMore):
    """
    互斥、依赖、包含
    """

    exclusive = ("exclusive", "互斥")
    dependent = ("dependent", "依赖")
    inclusive = ("inclusive", "包含")


class LogicalRelationEnum:
    """
    与、或、非
    """

    pass


class GenderEnum(StrEnumMore):
    """
    性别码表
    """

    male = ("male", "男")
    female = ("female", "女")


class SceneRole(StrEnumMore):
    """
    用户token预置角色
    """

    anonymous = ("anonymous", "匿名用户")
    user = ("user", "普通用户")


class PermissionEnum(StrEnumMore):
    """
    所有的权限判断都使用 apis.permissions.py 中的权限类
    所有权限为:  PermissionTypeEnum + MenuLevel2 + PermissionEnum
    """

    pass


class Status(StrEnumMore):
    enable = ("enable", "启用")
    disable = ("disable", "禁用")


class MessageType(StrEnumMore):
    text = ("text", "文本")
    picture = ("picture", "图片")
    video = ("video", "视频")
    audio = ("audio", "音频")
    # link = ("link", "链接") # 特殊的文本
    file = ("file", "文件")  # other File
    location = ("location", "定位")
    share = ("share", "分享")  # 分享好友、群组
    # sticker = ("sticker", "表情包")


class Protocol(StrEnumMore):
    https = ("https", "https")
    http = ("http", "http")
    rpc = ("rpc", "rpc")


# ==================================================
# 在该行上面新增 Enum 类
# ==================================================
# [("name", Enum)]
__enum_set__ = list(
    filter(
        lambda cls_name_and_cls: True
        if issubclass(cls_name_and_cls[1], (StrEnumMore, IntEnumMore))
        and cls_name_and_cls[1] not in [StrEnumMore, IntEnumMore]
        else False,
        inspect.getmembers(sys.modules[__name__], inspect.isclass),
    )
)

__enum_choices__ = list(
    map(lambda cls_name_and_cls: (cls_name_and_cls[0], cls_name_and_cls[1].__doc__.strip()), __enum_set__)
)


def get_enum_content(enum_name: str = None, is_reversed: bool = False):
    enum_content = {}
    enum_list = []  # type: List[Tuple[str, MyEnum]]
    if enum_name:
        try:
            enum_cls = getattr(sys.modules[__name__], enum_name)
            enum_list.append((enum_name, enum_cls))
        except (AttributeError, NotImplementedError):
            pass
    else:
        enum_list = __enum_set__

    for name, cls in enum_list:
        # if format_ == EnumInfoResponseFormats.list_.value:
        #     enum_content[name] = cls.choices()
        # else:
        if is_reversed:
            enum_content[name] = {v: k for k, v in cls.dict()}
        else:
            enum_content[name] = cls.dict()

    return enum_content
