from rest_framework import serializers

from storages import enums
from common.types import PlainSchema


class EnumQueryIn(PlainSchema):
    enum_name = serializers.ChoiceField(
        default=None, choices=enums.__enum_choices__, help_text=f"码表类名: {enums.__enum_choices__}"
    )
    is_reversed = serializers.BooleanField(default=False, help_text="是否反转键值")


template_name_choices = (("example", "示例"),)


class DownloadTemplateSerializer(PlainSchema):
    template_name = serializers.ChoiceField(help_text="模版名称", choices=template_name_choices,)
