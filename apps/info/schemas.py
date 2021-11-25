from rest_framework import serializers
from common.types import PlainSchema
from apps import enums


class EnumQueryIn(PlainSchema):
    enum_name = serializers.ChoiceField(choices=enums.__enum_choices__, help_text=f"码表类名: {enums.__enum_choices__}")
    format = serializers.ChoiceField(choices=enums.ChoiceResponseFormats.choices(),
                                     help_text=f"响应格式: {enums.ChoiceResponseFormats.choices()}")
