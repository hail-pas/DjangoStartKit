from rest_framework import serializers

from storages import enums
from common.types import PlainSchema
from common.drf.serializers import CustomJSONWebTokenSerializer


class LoginSerializer(CustomJSONWebTokenSerializer):  # noqa
    scene = serializers.CharField(required=False, default=enums.SceneRole.user.value, help_text="登录场景")

    # captcha = serializers.CharField(min_length=4, max_length=4, required=True,
    #                                 error_messages={
    #                                     "max_length": "图片验证码格式错误",
    #                                     "min_length": "图片验证码格式错误",
    #                                     "required": "请输入图片验证码"
    #                                 }, help_text="图片验证吗")
    # hash_key = serializers.CharField(required=True, write_only=True, allow_blank=False, help_text="图片验证码id")
    #
    # def validate_captcha(self, captcha):
    #     try:
    #         captcha = captcha.lower()
    #     except Exception:
    #         raise ValidationError("图片验证码错误")
    #     image_code = CaptchaStore.objects.filter(
    #         hashkey=self.initial_data['hash_key']).first()
    #     if not image_code:
    #         raise ValidationError("图片验证码错误")
    #     if timezone.now() > image_code.expiration:
    #         raise ValidationError("图片验证码过期")
    #     if image_code.response != captcha:
    #         raise ValidationError("图片验证码错误")
    #     # 防止验证码重放, 通过验证后删除
    #     image_code.delete()
    #     return captcha


class ChangePasswordSerializer(PlainSchema):
    old_password = serializers.CharField(required=True, help_text="旧密码")
    new_password = serializers.CharField(required=True, help_text="新密码", max_length=16, min_length=8)
    confirm_password = serializers.CharField(required=True, help_text="确认新密码", max_length=16, min_length=8)


class ReferenceIdSerializer(PlainSchema):
    referenced_id = serializers.CharField(max_length=32, required=True, help_text="关联id")


class InnerTokenIn(ReferenceIdSerializer):
    phone = serializers.CharField(max_length=11, required=True, help_text="手机号")
    scene = serializers.CharField(max_length=32, help_text="登录场景", allow_null=True, required=False)
