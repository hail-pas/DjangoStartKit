from urllib.parse import parse_qs

import ujson
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from rest_framework import status, exceptions
from django.utils.encoding import smart_text
from rest_framework.request import Request
from django.utils.translation import ugettext as _
from rest_framework.exceptions import ErrorDetail, ValidationError, AuthenticationFailed
from rest_framework_jwt.settings import api_settings
from rest_framework.authentication import get_authorization_header
from rest_framework_jwt.authentication import JSONWebTokenAuthentication, jwt_decode_handler, \
    jwt_get_username_from_payload

from common.types import ContentTypeEnum, RequestMethodEnum
from apps.responses import RestResponse


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
        request.json_data = None

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
            if body_serializer and request.content_type == ContentTypeEnum.APPlICATION_JSON.value:
                # 只校验json传输
                data = ujson.loads((request.body or b"{}").decode("utf8"))
                b_ser = body_serializer(data=data)
                b_ser.is_valid(raise_exception=True)
                request.json_data = b_ser.validated_data
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

    """

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
            # 401 直接返回
            if response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
                return response
            data = response.data
            if isinstance(data, dict):
                error_field, error_value = list(data.items())[0]
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

    def get_jwt_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = api_settings.JWT_AUTH_HEADER_PREFIX.lower()

        if not auth:
            if api_settings.JWT_AUTH_COOKIE:
                return request.COOKIES.get(api_settings.JWT_AUTH_COOKIE)
            return None

        if smart_text(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:
            msg = _("Invalid Authorization header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)

        return auth[1]


class AuthenticationMiddlewareJWT:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest):
        try:
            parsed = CustomJSONWebTokenAuthentication().authenticate(Request(request))
            if parsed:
                (user, user_jwt) = parsed
                request._user = user
        except AuthenticationFailed:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response


class ChannelsAuthenticationMiddlewareJWT(BaseMiddleware):

    def __init__(self, inner):
        """
        Middleware constructor - just takes inner application.
        """
        self.inner = inner

    @database_sync_to_async
    def get_user(self, jwt_value):
        from django.contrib.auth.models import AnonymousUser
        _user = AnonymousUser()
        if not jwt_value:
            return _user
        try:
            payload = jwt_decode_handler(jwt_value)
        except:  # noqa
            pass
        else:
            User = get_user_model()
            username = jwt_get_username_from_payload(payload)

            try:
                temp_user = User.objects.get_by_natural_key(username)
                if temp_user.is_active and not temp_user.delete_time:
                    _user = temp_user
            except User.DoesNotExist:
                pass

        return _user

    async def __call__(self, scope, receive, send):
        """
        ASGI application; can insert things into the scope and run asynchronous
        code.
        """
        # Copy scope to stop changes going upstream
        scope = dict(scope)
        query_param = parse_qs(scope["query_string"].decode())
        token = query_param.get("token")
        if token:
            token = token[0]
        scope["user"] = await self.get_user(token)

        # Run the inner application along with the scope
        return await super().__call__(scope, receive, send)
