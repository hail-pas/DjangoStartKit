import logging
from math import ceil
from typing import Optional, Any
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone
from drf_yasg.utils import filter_none
from pydantic import BaseModel

from apps.enums import ResponseCodeEnum

logger = logging.getLogger(__name__)


class _PageInfo(BaseModel):
    """
    翻页相关信息
    """
    total_page: int
    page_size: int
    page_num: int


class _Resp(BaseModel):
    """"
    响应体格式
    res = {
        "code": 200,  # http状态码为 200 前提下自定义code
        "success": True
        "response_time": "datetime",
        "message": "message",
        "data": "data"
        }
    """

    code: int = ResponseCodeEnum.success.value
    success: bool = True
    response_time: datetime = timezone.now()
    message: Optional[str] = "success"
    data: Optional[Any] = None
    page_info: Optional[_PageInfo] = None


class RestResponse(JsonResponse):
    """
    真实响应
    """

    def __init__(self, code: int = ResponseCodeEnum.success.value, success: bool = True,
                 response_time: datetime = timezone.now(),
                 message: Optional[str] = None, data: Optional[Any] = None, encoder=DjangoJSONEncoder,
                 page_size: int = None, page_num: int = None, total_count: int = None, **kwargs):
        page_info = None
        if all([page_size, page_num, total_count]):
            page_info = _PageInfo(page_size=page_size, page_num=page_num, total_page=ceil(total_count / page_size))
        super().__init__(
            filter_none(_Resp(code=code, success=success, response_time=response_time, message=message, data=data,
                              page_info=page_info).dict()), encoder, safe=True, json_dumps_params=None, **kwargs)

    @classmethod
    def ok(cls, message: Optional[str] = "", data: Optional[Any] = None):
        return RestResponse(message=message, data=data)
