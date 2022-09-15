"""
自定义 APIException
"""
from rest_framework import status  # noqa
from rest_framework.exceptions import APIException  # noqa

from common import messages
from storages import enums


class GeneralServiceException(APIException):
    """
    用户 token payload scene 校验未通过
    """

    default_detail = messages.UserSceneCheckFailed
    default_code = enums.ResponseCodeEnum.failed.value
