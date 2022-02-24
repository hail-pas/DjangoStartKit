"""
全部的Enum类型
"""
import enum
import inspect
import sys
from enum import unique, Enum
from typing import List, Tuple

from common.types import StrEnumMore, IntEnumMore, MyEnum


@unique
class ResponseCodeEnum(IntEnumMore):
    """
    业务响应代码，除了500之外都在200的前提下返回对用code
    """

    # 唯一成功响应
    success = (100200, "成功")

    # HTTP 状态码  2xx - 5xx
    # 100{[2-5]]xx}, http status code 拼接

    # 失败响应，999倒序取
    failed = (100999, "失败")


# class EnumInfoResponseFormats(StrEnumMore):
#     """
#     码表信息响应格式
#     """
#     json_ = ("json", "Json")
#     list_ = ("list", "数组")

class GroupTypeEnum(StrEnumMore):
    """
    分组码表
    function = ("function", "功能")
    interface = ("interface", "接口")
    """
    menu = ("menu", "菜单")
    permission = ("permission", "权限聚合组")


class PermissionTypeEnum(StrEnumMore):
    """
    权限组预置 code, 目前只有：查看 和 操作
    """
    view = ("view", "查看权限")
    operate = ("operate", "操作权限")


class MenuLevel1(StrEnumMore):
    """
    一级菜单
    """
    index = ("index", "首页")


class MenuLevel2(StrEnumMore):
    """
    二级菜单
    """
    index_ = ("index_main", "首页主页面")


class PermissionEnum(StrEnumMore):
    """
    自定义权限码表, 集成自 MenuLevel2, 将二级菜单映射成权限
    所有的权限判断都使用 apps.permissions.py 中的权限类
    所有权限为:  PermissionTypeEnum + MenuLevel2 + PermissionEnum
    """
    pass


class RoleCodeEnum(StrEnumMore):
    """
    预置角色码表
    """
    super_admin = ("super_admin", "超管")


class GenderEnum(StrEnumMore):
    """
    性别码表
    """
    male = ("male", "男")
    female = ("female", "女")


# ==================================================
# 在该行上面新增 Enum 类
# ==================================================
# [("name", Enum)]
__enum_set__ = list(filter(
    lambda cls_name_and_cls:
    True if issubclass(cls_name_and_cls[1], (StrEnumMore, IntEnumMore))
            and cls_name_and_cls[1] not in [StrEnumMore, IntEnumMore]
    else False,
    inspect.getmembers(sys.modules[__name__], inspect.isclass)
))

__enum_choices__ = list(
    map(
        lambda cls_name_and_cls:
        (cls_name_and_cls[0], cls_name_and_cls[1].__doc__.strip()),
        __enum_set__
    )
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
