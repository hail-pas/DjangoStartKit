import logging

from drf_yasg import openapi
from django.db import models
from rest_framework import status
from drf_yasg.openapi import IN_QUERY, TYPE_STRING, Parameter
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import NotHandled, SwaggerAutoSchema, CoreAPICompatInspector
from rest_framework.utils import formatting
from django.utils.encoding import smart_str
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.schemas import AutoSchema
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication

from common.utils import model_to_dict
from apps.responses import RestResponse, _Resp  # noqa
from common.schemas import PageParam

DRF_GENERATE_METHODS = [
    "retrieve",
    "list",
    "create",
    "update",
    "partial_update",
    "destroy",
]
DRF_GENERATE_METHODS_DESCRIPTION = {
    "retrieve": "获取{}详情",
    "list": "获取{}列表",
    "create": "创建{}",
    "update": "全量更新{}",
    "partial_update": "部分更新{}",
    "destroy": "删除{}",
}


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
        simple_list = getattr(self.request, "raw_simple_list", [])
        if simple_list:
            data = [model_to_dict(d, simple_list) if isinstance(d, models.Model) else d for d in data]
        return RestResponse(
            data=data["data"] if isinstance(data, dict) else data,
            page_size=self.get_page_size(self.request),
            page_num=self.page.number,
            total_count=self.page.paginator.count,
        )


class JSONFormatter(logging.Formatter):
    """
    Logging Formatter to add colors and count warning / errors
    """

    #  "exec": "%(pathname)s", "func": "%(funcName)s"
    format = (
        '{"asctime": "%(asctime)s", "process": %(process)d, "levelname": "%(levelname)s", '
        '"filename": "%(pathname)s", "name": "%(funcName)s", "lineno": %(lineno)d, "message": "%(message)s"}'
    )
    FORMATS = {
        logging.DEBUG: format,
        logging.INFO: format,
        logging.WARNING: format,
        logging.ERROR: format,
        logging.CRITICAL: format,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class CustomAutoSchema(AutoSchema):
    def get_description(self, path, method):
        """
        Determine a path description.

        This will be based on the method docstring if one exists,
        or else the class docstring.
        """
        view = self.view

        method_name = getattr(view, "action", method.lower())
        method_docstring = getattr(view, method_name, None).__doc__
        if method_docstring:
            # An explicit docstring on the method or action.
            return self._get_description_section(view, method.lower(), formatting.dedent(smart_str(method_docstring)))
        else:
            if method_name in DRF_GENERATE_METHODS and view.queryset is not None:
                return DRF_GENERATE_METHODS_DESCRIPTION[method_name].format(view.queryset.model._meta.label)  # noqa
            return self._get_description_section(
                view, getattr(view, "action", method.lower()), view.get_view_description()
            )


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def __init__(self, view, path, method, components, request, overrides, operation_keys=None):
        super(SwaggerAutoSchema, self).__init__(view, path, method, components, request, overrides)
        self._sch = CustomAutoSchema()
        self._sch.view = view
        self.operation_keys = operation_keys

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
            if create_response:
                create_schema = create_response.get("schema")
                responses.update(
                    {
                        status_code: openapi.Response(
                            create_response.get("description", ""),
                            _Resp.to_schema(create_schema),
                            create_response.get("examples", None),
                        )
                    }
                )
        elif action in ["list", "retrieve", "update", "partial_update"]:
            status_code = str(status.HTTP_200_OK)
            _response = responses.get(status_code)  # type: openapi.Response
            _schema = _response.get("schema")
            ret_schema = _Resp.to_schema(_schema)
            if action == "list" and getattr(_schema, "properties", None):
                _schema = _schema.properties.get("results")
                ret_schema = _Resp.to_schema(_schema, page_info=True)
            responses.update(
                {
                    status_code: openapi.Response(
                        _response.get("description", ""), ret_schema, _response.get("examples", None)
                    )
                }
            )
        return responses

    def get_query_parameters(self):
        params = super(CustomSwaggerAutoSchema, self).get_query_parameters()
        action = getattr(self.view, "action", None)
        if action and action == "list":
            for param in params:
                if param.name == "search" and getattr(self.view, "search_fields", None):
                    if getattr(self.view, "search_fields", None):
                        param.description = f"搜索字段: {', '.join(self.view.search_fields)}"  # noqa
                    else:
                        params.remove(param)
            simple_list_param = Parameter(
                name="simple_list",
                in_=IN_QUERY,
                description=f"英文逗号分隔, 指定返回字段: "
                f"{', '.join([i.name for i in self.view.get_serializer_class().Meta.model._meta.fields])}",
                # noqa
                required=False,
                type=TYPE_STRING,
            )
            return [simple_list_param] + params
        return params


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_operation_keys(self, sub_path, method, view):
        str_list: list = self._gen.get_keys(sub_path, method, view)
        if str_list[-1] == "read" and view.action not in DRF_GENERATE_METHODS:
            str_list = str_list[:-1]
        return str_list


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
