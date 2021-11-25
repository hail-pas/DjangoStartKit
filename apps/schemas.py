from rest_framework import serializers
from common.types import RequestSchema


class PageParam(RequestSchema):
    page_size = serializers.IntegerField(help_text="页大小")
    page_num = serializers.IntegerField(help_text="页码")
    total_page = serializers.IntegerField(help_text="总页数")


class HbasePageParam(RequestSchema):
    start_row_key = serializers.CharField(help_text="起始row_key")
    page_size = serializers.IntegerField(help_text="页大小")
