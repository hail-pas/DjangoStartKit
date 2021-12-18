from common.types import PlainSchema
from rest_framework import serializers
from apps.account.serializers import ProfileSerializer, CustomizeGroupListSerializer


class CaptchaResponse(PlainSchema):
    hash_key = serializers.CharField(help_text='图形验证码hash key')
    image_url = serializers.CharField(help_text='图形验证码图片地址')


class LoginResponse(PlainSchema):
    token = serializers.CharField(help_text="token")
    user = ProfileSerializer()
    menu = CustomizeGroupListSerializer()
