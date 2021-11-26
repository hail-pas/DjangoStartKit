import inspect
from http import HTTPStatus
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers

from apps.responses import _Resp  # noqa


def custom_swagger_auto_schema(**kwargs):
    """
    通过 query_serializer、request_body 校验 param、json 传参, validated_data 存入 request.param_data、 request.json_data
    """

    def decorator(func):
        responses = kwargs.get("responses")
        if responses:
            responses_200_ser = responses.get(str(HTTPStatus.OK.value))  # noqa
            if responses_200_ser:
                page_info = kwargs.get("page_info", False)

                _is_serializer_class = inspect.isclass(responses_200_ser) and issubclass(responses_200_ser,
                                                                                         serializers.Serializer)
                _is_serializer_instance = isinstance(responses_200_ser, serializers.Serializer)
                _is_list_serializer_instance = isinstance(responses_200_ser, serializers.ListSerializer)

                assert (
                        _is_serializer_class or _is_serializer_instance or _is_list_serializer_instance
                ), f"AssertionError: Serializer class or instance required, not {type(responses_200_ser)}"

                if _is_serializer_class:
                    if page_info:
                        responses_200_ser = responses_200_ser(many=True)
                    else:
                        responses_200_ser = responses_200_ser()
                if _is_serializer_instance and page_info:
                    raise RuntimeError("Single Response Item Cannot with PageInfo")
                kwargs['responses'][str(HTTPStatus.OK.value)] = _Resp.to_serializer(  # noqa
                    resp_serializer=responses_200_ser,
                    page_info=page_info)
        view_method = swagger_auto_schema(**kwargs)(func)
        view_method.query_serializer = kwargs.get("query_serializer", None)
        view_method.body_serializer = kwargs.get("request_body", None)
        return view_method

    return decorator
