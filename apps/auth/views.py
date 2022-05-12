from django.utils import timezone
from captcha.models import CaptchaStore
from rest_framework import views
from captcha.helpers import captcha_image_url
from django.contrib.auth import logout
from rest_framework.parsers import JSONParser
from rest_framework_jwt.views import ObtainJSONWebToken
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.auth import schemas, serializers
from apps.responses import RestResponse
from common.swagger import custom_swagger_auto_schema
from apps.account.models import Profile, SystemResource
from apps.account.serializers import ProfileSerializer, get_profile_system_resource


class CaptchaView(views.APIView):
    """图形验证码
    get:
        Return captcha hash_key and image_url
    """

    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    @custom_swagger_auto_schema(responses={"200": serializers.CaptchaResponse})
    def get(self, request, *args, **kwargs):
        hash_key = CaptchaStore.generate_key()
        return RestResponse.ok(
            data={"hash_key": hash_key, "image_url": request.build_absolute_uri(captcha_image_url(hash_key))}
        )


class LoginView(ObtainJSONWebToken):
    """登陆
    """

    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    @custom_swagger_auto_schema(request_body=schemas.LoginSerializer, responses={"200": serializers.LoginResponse})
    def post(self, request, *args, **kwargs):
        profile = request.json_data["user"]
        if not profile:
            return RestResponse.fail(message="账号或用户名错误")

        if not profile.is_active:
            return RestResponse.fail(message="该账号已被禁用")

        if profile.deleted:
            return RestResponse.fail(message="该账号已被归档")

        profile.last_login = timezone.now()
        profile.save(update_fields=["last_login"])
        return RestResponse.ok(
            data={
                "token": request.json_data["token"],
                "user": ProfileSerializer(instance=profile).data,
                "menu": get_profile_system_resource(
                    profile,
                    SystemResource.objects.filter(parent=None)
                    & SystemResource.objects.filter(
                        id__in=profile.roles.all().values_list("system_resources__id", flat=True)
                    ),
                ),
            }
        )


class ChangePasswordView(ObtainJSONWebToken):
    """
    修改密码
    """

    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    @custom_swagger_auto_schema(request_body=schemas.ChangePasswordSerializer)
    def post(self, request, *args, **kwargs):
        profile = request.user  # type: Profile

        if profile.deleted:
            return RestResponse.fail(message="该账号已被归档")

        if not profile.is_active:
            return RestResponse.fail(message="该账号已被禁用")

        old_password = request.json_data["old_password"]
        new_password = request.json_data["new_password"]
        confirm_password = request.json_data["confirm_password"]

        if not profile.check_password(old_password):
            return RestResponse.fail(message="旧密码验证不通过")

        if new_password != confirm_password:
            return RestResponse.fail(message="新密码和确认密码不一致，请重新输入")

        if new_password == old_password:
            return RestResponse.fail(message="新密码不能和旧密码相同")

        profile.set_password(new_password)
        profile.save()
        logout(request)
        return RestResponse.ok()
