from urllib.parse import parse_qs

import jwt
import ujson
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import no_body
from rest_framework import status, exceptions
from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import ugettext as _
from rest_framework.renderers import JSONRenderer
from rest_framework.exceptions import ErrorDetail, ValidationError, AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from rest_framework_jwt.authentication import (
    JSONWebTokenAuthentication,
    jwt_decode_handler,
    jwt_get_username_from_payload,
)

from common import messages
from storages import enums
from conf.config import local_configs
from common.types import ContentTypeEnum, RequestMethodEnum
from apis.responses import RestResponse


class RequestProcessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # Code to be executed for each request/response after
        # the view is called.
        return self.get_response(request)

    def process_view(self, request: HttpRequest, view_processor, *view_args, **view_kwargs):
        """
        view 参数自动校验封装进 request.GET,  request.DATA
        params 传参 -> request.GET  #type: QueryDict
        from-urlencode 传参 -> request.POST/body,   QueryDict/bytes
        form-data 传参 -> request.POST  # type: QueryDict
        json 传参 -> request.body # type: bytes
        :param request:
        :param view_processor:
        :param view_args:
        :param view_kwargs:
        :return:
        """
        request.param_data = None
        request.body_data = None

        if request.method.lower() in [
            RequestMethodEnum.OPTIONS.value,
            RequestMethodEnum.HEAD.value,
            RequestMethodEnum.CONNECT.value,
            RequestMethodEnum.TRACE.value,
        ]:
            return
        cls = getattr(view_processor, "cls", None)
        if not cls:
            return
        actions = getattr(view_processor, "actions", None)
        # APIView
        query_serializer = getattr(view_processor, "query_serializer", None)
        body_serializer = getattr(view_processor, "body_serializer", None)
        # ViewSet
        if actions:
            view_func = getattr(cls, actions.get(request.method.lower(), ""), "")
        else:
            view_func = getattr(cls, request.method.lower(), "")

        if view_func:
            if not query_serializer:
                query_serializer = getattr(view_func, "query_serializer", None)

            if not body_serializer:
                body_serializer = getattr(view_func, "body_serializer", None)

        try:
            if query_serializer:
                q_ser = query_serializer(data=request.GET)
                q_ser.is_valid(raise_exception=True)
                request.param_data = q_ser.validated_data
            if body_serializer and body_serializer != no_body:
                if request.content_type == ContentTypeEnum.APPlICATION_JSON.value:
                    # json传输
                    data = ujson.loads((request.body or b"{}").decode("utf8"))
                else:
                    data = request.POST.dict()
                    data.update(request.FILES.dict())
                b_ser = body_serializer(data=data)
                b_ser.is_valid(raise_exception=True)
                request.body_data = b_ser.validated_data
        except ValidationError as valid_error:
            # {'ids': {0: [ErrorDetail(string='请填写合法的整数值。', code='invalid')]}}
            # {'ids': [ErrorDetail(string='测试', code='invalid')]}

            def get_error_detail_msg(e_d):
                if isinstance(e_d, dict):
                    for _k, _v in e_d.items():
                        if isinstance(v, ErrorDetail):
                            return f"{_k}: {_v}"
                elif isinstance(e_d, list):
                    for i in e_d:
                        if isinstance(i, ErrorDetail):
                            return i

                return e_d

            _msg = ""
            error_detail = valid_error.detail
            for k, v in error_detail.items():
                _msg += get_error_detail_msg(v)
            return RestResponse.fail(message=_msg, data=error_detail)


class ResponseProcessMiddleware:
    """
    响应处理，>= 400 的 http 状态码只返回特定的
    """

    ESCAPE_HTTP_STATUS_CODE = [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response

    def process_template_response(self, request, response):  # noqa
        # 处理 exception response
        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            # 直接返回的状态码
            if response.status_code in self.ESCAPE_HTTP_STATUS_CODE:
                if response.status_code == status.HTTP_403_FORBIDDEN and not request.META.get("HTTP_AUTHORIZATION"):
                    # 未携带授权头时报403返回 401 状态码
                    response.status_code = status.HTTP_401_UNAUTHORIZED
                return response
            data = response.data
            if isinstance(data, dict):
                if response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
                    # ServiceException
                    response.data = RestResponse(
                        code=data["detail"].code, message=data["detail"], data=data, success=False
                    ).dict()
                else:
                    _, error_value = list(data.items())[0]
                    if error_value and isinstance(error_value, list):
                        error_value = error_value[0]
                    msg = error_value
                    # if error_field not in ["non_field_errors", "detail"]:
                    #     msg = f"错误字段: {error_field}-{error_value}"
                    #     # msg = f"{error_value}"
                    response.data = RestResponse.fail(message=msg, data=data).dict()

            elif isinstance(data, str):
                response.data = RestResponse.fail(message=data).dict()

            elif isinstance(data, list):
                response.data = RestResponse.fail(message=",".join(data), data=data).dict()

            response.status_code = status.HTTP_200_OK

        return response


class CustomJSONWebTokenAuthentication(JSONWebTokenAuthentication):
    """
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string specified in the setting
    `JWT_AUTH_HEADER_PREFIX`. For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """

    www_authenticate_realm = "api"

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            return None

        try:
            payload = jwt_decode_handler(jwt_value)
        except jwt.ExpiredSignature:
            msg = _("Signature has expired.")
            raise exceptions.AuthenticationFailed(msg)
        except jwt.DecodeError:
            msg = _("Error decoding signature.")
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed()

        user = self.authenticate_credentials(payload)

        return user, jwt_value, payload

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        User = get_user_model()
        username = jwt_get_username_from_payload(payload)

        if not username:
            msg = _("Invalid payload.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            msg = _("Invalid signature.")
            raise exceptions.AuthenticationFailed(msg)

        if not user.is_active:
            msg = _("User account is disabled.")
            raise exceptions.AuthenticationFailed(msg)

        return user


def middleware_response(status, data: dict):  # noqa
    response = Response(data=data, status=status)
    response.accepted_renderer = JSONRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    response.render()
    return response


class AuthenticationMiddlewareJWT:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest):
        try:
            parsed = CustomJSONWebTokenAuthentication().authenticate(Request(request))
            if parsed:
                (user, _, payload) = parsed
                request._user = user
                request.user = user
                request.scene = payload.get("scene")
                request.system = payload.get("system")
                if (user.is_staff or user.is_superuser) and not (
                    request.path.startswith("/admin") or request.path.startswith("/static/admin")
                ):  # disable admin user
                    return middleware_response(
                        status=status.HTTP_403_FORBIDDEN,
                        data={"message": messages.Forbidden.format("admin用户对非admin接口")},
                    )

                if (
                    # and request.scene not in enums.SceneRole.anonymous.value
                    request.scene
                    not in user.role_names + enums.SceneRole.values  # 预置角色和自定义角色
                    # TODO: 校验用户请求系统的合法性
                ):
                    return middleware_response(
                        status=status.HTTP_401_UNAUTHORIZED, data={"message": messages.UserSceneCheckFailed}
                    )
            else:
                request._user = AnonymousUser()
                request.scene = enums.SceneRole.anonymous.value
                request.system = local_configs.PROJECT.NAME
        except AuthenticationFailed:
            # request._user = AnonymousUser()
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)
            # request.scene = enums.SceneRole.anonymous.value
            # request.system = local_configs.PROJECT.NAME

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response
