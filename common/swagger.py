from drf_yasg.inspectors import PaginatorInspector
from drf_yasg.utils import swagger_auto_schema


def swagger_add_request_serializer(**kwargs):
    def decorator(func):
        view_method = swagger_auto_schema(**kwargs)(func)
        view_method.query_serializer = kwargs.get("query_serializer", None)
        view_method.body_serializer = kwargs.get("request_body", None)
        return view_method

    return decorator


def single_api_swagger():
    """
    单接口
    :return:
    """

    def decorator(func):
        view_method = swagger_auto_schema()(func)
        return view_method

    return decorator


def page_api_swagger():
    """
    翻页相关接口
    :return:
    """
    pass


def hbase_page_api_swagger():
    """
    hbase 翻页相关
    :return:
    """
    pass
