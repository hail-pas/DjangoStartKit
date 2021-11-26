import json
import logging
from functools import lru_cache
from math import ceil
from typing import Optional, Any
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone
from drf_yasg.utils import filter_none
from pydantic import BaseModel
from rest_framework import serializers

from apps.enums import ResponseCodeEnum
from common.types import PlainSchema

logger = logging.getLogger(__name__)


class _PageInfo(BaseModel):
    """
    翻页相关信息
    """
    total_page: int
    page_size: int
    page_num: int

    @classmethod
    @lru_cache
    def to_serializer(cls):
        class PageInfo(PlainSchema):
            total_page = serializers.IntegerField(default=1, help_text="总页数")
            page_size = serializers.IntegerField(default=10, help_text="每页条数")
            page_num = serializers.IntegerField(default=1, help_text="当前页码")

        return PageInfo


# class _Resp(GenericModel, Generic[DataT]):
class _Resp(BaseModel):
    """"
    响应体格式
    res = {
        "code": 200,  # http状态码为 200 前提下自定义code
        "success": True
        "message": "message",
        "data": "data"
        }
    """

    code: int = ResponseCodeEnum.success.value
    success: bool = True
    message: Optional[str] = "success"
    data: Optional[Any] = None
    page_info: Optional[_PageInfo] = None

    @classmethod
    def to_serializer(cls, resp_serializer, page_info: bool = False):

        def generate_serializer(_name: str):

            attrs = {
                "code": serializers.ChoiceField(default=ResponseCodeEnum.success.value,
                                                choices=ResponseCodeEnum.choices(),
                                                help_text=f"响应状态码: {ResponseCodeEnum.choices()}"),
                "success": serializers.BooleanField(default=True, help_text="是否成功"),
                "message": serializers.CharField(default="", help_text="响应信息"),
                "data": resp_serializer,
            }

            class Meta:
                ref_name = _name

            attrs["Meta"] = Meta

            if "Page" in _name:
                attrs["page_info"] = _PageInfo.to_serializer()()
            return type(_name, (PlainSchema,), attrs)

        _cache = {}

        if isinstance(resp_serializer, serializers.ListSerializer):
            if page_info:
                name = f"PageResp{resp_serializer.child.__class__.__name__}"
            else:
                name = f"ListResp{resp_serializer.child.__class__.__name__}"
        elif isinstance(resp_serializer, serializers.Serializer):
            name = f"Resp{resp_serializer.__class__.__name__}"
        else:
            raise RuntimeError("Should Use Serializer class or ListSerializer instance as Response Schema")

        if not _cache.get(name, None):
            _cache[name] = generate_serializer(name)

        return _cache[name]


class RestResponse(JsonResponse):
    """
    真实响应
    """

    result: Any = None

    def __init__(self, code: int = ResponseCodeEnum.success.value, success: bool = True,
                 message: Optional[str] = None, data: Optional[Any] = None, encoder=DjangoJSONEncoder,
                 page_size: int = None, page_num: int = None, total_count: int = None, **kwargs):
        page_info = None
        if all([page_size, page_num, total_count]):
            page_info = _PageInfo(page_size=page_size, page_num=page_num, total_page=ceil(total_count / page_size))
        self.result = filter_none(
            _Resp(code=code, success=success, message=message, data=data,
                  page_info=page_info).dict())
        super().__init__(self.result
                         , encoder, safe=True, json_dumps_params=None, **kwargs)

    @classmethod
    def ok(cls, message: Optional[str] = "", data: Optional[Any] = None):
        return RestResponse(message=message, data=data)

    @classmethod
    def fail(cls, message: str = ""):
        return RestResponse(code=ResponseCodeEnum.failed.value, success=False, message=message)

    def dict(self):
        return self.result
