import logging
import math

from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.responses import _Resp  # noqa


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    关闭csrf
    """

    def enforce_csrf(self, request):
        return


class CustomPagination(PageNumberPagination):
    """分页
    """
    page_size_query_param = 'page_size'
    page_size = 10

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        total_page = math.ceil(self.page.paginator.count / page_size)
        response = dict([
            ('page_size', page_size),
            ('count', self.page.paginator.count),
            ('current_page', self.page.number),
            ('total_page', total_page),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('data', data['data'] if isinstance(data, dict) else data),
        ])
        if not isinstance(data, list):
            for key in [i for i in data.keys() if i != 'data']:
                response[key] = data[key]

        return Response(response)


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
                ret_schema = _Resp.to_schema(_schema, page_info=True)
            responses.update(
                {status_code: openapi.Response(_response.get("description", ""),
                                               ret_schema,
                                               _response.get("examples", None))})
        elif action == "destroy":
            status_code = str(status.HTTP_204_NO_CONTENT)
            destroy_response = responses.get(status_code)  # type: openapi.Response
            destroy_schema = destroy_response.get("schema")
            responses.update(
                {status_code: openapi.Response(destroy_response.get("description", ""),
                                               destroy_schema,
                                               destroy_response.get("examples", None))})
        return responses
