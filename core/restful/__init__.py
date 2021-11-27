import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema, CoreAPICompatInspector, NotHandled
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination

from apps.responses import _Resp, RestResponse  # noqa
from common.schemas import PageParam


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    关闭csrf
    """

    def enforce_csrf(self, request):
        return


class CustomPagination(PageNumberPagination):
    """分页
    """

    page_query_param = PageParam.Enum.page_num.value
    page_query_description = PageParam.Enum.dict().get(PageParam.Enum.page_num.value)

    # Client can control the page size using this query parameter.
    # Default is 'None'. Set to eg 'page_size' to enable usage.
    page_size_query_param = PageParam.Enum.page_size.value
    page_size_query_description = PageParam.Enum.dict().get(PageParam.Enum.page_size.value)

    page_size = 10

    def get_paginated_response(self, data):
        return RestResponse(data=data['data'] if isinstance(data, dict) else data,
                            page_size=self.get_page_size(self.request), page_num=self.page.number,
                            total_count=self.page.paginator.count)


class CustomLogFormatter(logging.Formatter):
    """
    Logging Formatter to add colors and count warning / errors
    """

    grey = "\x1b[38;21m"
    green = "\x1b[32;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = '{"level": "%(levelname)s", "time": "%(asctime)s", "exec": "%(pathname)s", "func": "%(funcName)s", ' \
             '"msg": "%(message)s"} '
    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class CustomSwaggerAutoSchema(SwaggerAutoSchema):

    def get_responses(self):
        responses = super().get_responses()

        # rest_schema = openapi.Schema(description="状态吗", )
        # openapi.Response('response description', UserSerializer)
        action = getattr(self.view, "action", None)
        if not action:
            return responses
        if action == "create":
            status_code = str(status.HTTP_201_CREATED)
            create_response = responses.get(status_code)  # type: openapi.Response
            create_schema = create_response.get("schema")
            responses.update(
                {status_code: openapi.Response(create_response.get("description", ""),
                                               _Resp.to_schema(create_schema),
                                               create_response.get("examples", None))})
        elif action in ["list", "retrieve", "update", "partial_update"]:
            status_code = str(status.HTTP_200_OK)
            _response = responses.get(status_code)  # type: openapi.Response
            _schema = _response.get("schema")
            ret_schema = _Resp.to_schema(_schema)
            if action == "list":
                _schema = _schema.properties.get("results")
                ret_schema = _Resp.to_schema(_schema, page_info=True)
            responses.update(
                {status_code: openapi.Response(_response.get("description", ""),
                                               ret_schema,
                                               _response.get("examples", None))})
        return responses


class NoPagingAutoSchema(CustomSwaggerAutoSchema):
    """No page and page_size parameters in swagger
    """

    def should_page(self):
        return False


class HideInspector(CoreAPICompatInspector):
    """No unused parameters in swagger
    """

    def get_filter_parameters(self, filter_backend):
        if type(filter_backend) in (OrderingFilter, SearchFilter, DjangoFilterBackend):
            return
        return NotHandled
