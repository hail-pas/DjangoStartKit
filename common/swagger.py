import inspect
from http import HTTPStatus
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers

from apps.responses import _Resp  # noqa


def custom_swagger_auto_schema(**kwargs):
    def decorator(func):
        responses = kwargs.get("responses")
        if responses:
            responses_200_ser = responses.get(str(HTTPStatus.OK.value))
            if responses_200_ser:
                page_info = kwargs.get("page_info", False)
                if inspect.isclass(responses_200_ser) and issubclass(responses_200_ser, serializers.Serializer):
                    if page_info:
                        responses_200_ser = responses_200_ser(many=True)
                    else:
                        responses_200_ser = responses_200_ser()
                elif isinstance(responses_200_ser, serializers.ListSerializer):
                    responses_200_ser = responses_200_ser
                elif isinstance(responses_200_ser, serializers.Serializer):
                    if page_info:
                        raise RuntimeError("Single Response Item Cannot with PageInfo")
                    responses_200_ser = responses_200_ser
                else:
                    raise RuntimeError("Should Use Serializer class or ListSerializer instance as Response Schema")
                kwargs['responses'][str(HTTPStatus.OK.value)] = _Resp.to_serializer(
                    resp_serializer=responses_200_ser,
                    page_info=page_info)
        view_method = swagger_auto_schema(**kwargs)(func)
        view_method.query_serializer = kwargs.get("query_serializer", None)
        view_method.body_serializer = kwargs.get("request_body", None)
        return view_method

    return decorator
