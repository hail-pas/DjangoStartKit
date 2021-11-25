"""
全部的Enum类型
"""
import inspect
import sys
from enum import unique

from common.types import StrEnumMore, IntEnumMore


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


class ChoiceResponseFormats(StrEnumMore):
    """
    码表信息响应格式
    """
    json_ = ("json", "Json")
    list_ = ("list", "数组")


class RoleCodes(StrEnumMore):
    """
    角色码表
    """
    super_admin = ("super_admin", "超管")


# ==================================================
# 在改行上面新增 Enum 类
# ==================================================

__enum_choices__ = list(
    map(
        lambda cls_name_and_cls:
        (cls_name_and_cls[0], cls_name_and_cls[1].__doc__.strip()),
        filter(
            lambda cls_name_and_cls:
            True if issubclass(cls_name_and_cls[1], (StrEnumMore, IntEnumMore))
                    and cls_name_and_cls[1] not in [StrEnumMore, IntEnumMore]
            else False,
            inspect.getmembers(sys.modules[__name__], inspect.isclass)
        )
    )
)
