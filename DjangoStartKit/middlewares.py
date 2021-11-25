import ujson
from django.http import HttpRequest
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from common.types import RequestMethodEnum, ContentTypeEnum


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

        if request.method.lower() in [RequestMethodEnum.OPTIONS.value, RequestMethodEnum.HEAD.value,
                                      RequestMethodEnum.CONNECT.value, RequestMethodEnum.TRACE.value]:
            return
        actions = getattr(view_processor, "actions", None)
        if issubclass(view_processor.cls, APIView):
            # APIView
            query_serializer = getattr(view_processor, "query_serializer", None)
            body_serializer = getattr(view_processor, "body_serializer", None)
        elif actions:
            # ViewSet
            view_func = getattr(view_processor.cls, actions.get(request.method.lower(), ""), "")
            if not view_func:
                return
            query_serializer = getattr(view_func, "query_serializer", None)
            body_serializer = getattr(view_func, "body_serializer", None)

        else:
            return

        try:
            if query_serializer:
                q_ser = query_serializer(data=request.GET)
                q_ser.is_valid(raise_exception=True)
                request.GET = q_ser.validated_data
            if body_serializer and request.content_type == ContentTypeEnum.APPlICATION_JSON.value:
                # 只校验json传输
                data = ujson.loads(request.body.decode('utf8'))
                b_ser = body_serializer(data=data)
                b_ser.is_valid(raise_exception=True)
                request.POST = q_ser.validated_data
        except ValidationError as valid_error:
            raise valid_error


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
