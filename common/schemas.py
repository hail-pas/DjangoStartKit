"""
翻页通用schema
"""

from rest_framework import serializers
from common.types import PlainSchema, StrEnumMore


class PageParam(PlainSchema):
    page_size = serializers.IntegerField(help_text="页大小", default=10, min_value=1)
    page_num = serializers.IntegerField(help_text="页码", default=1, min_value=1)

    class Enum(StrEnumMore):
        page_size = ("page_size", "每页条数")
        page_num = ("page_num", "页码")


class HbasePageParam(PlainSchema):
    start_row_key = serializers.CharField(help_text="起始row_key", required=False, default="")
    page_size = serializers.IntegerField(help_text="页大小", default=10, required=False)
