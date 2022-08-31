from rest_framework import status
from django.core.exceptions import FieldError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common import messages
from core.restful import CustomPagination
from apps.responses import RestResponse


class CustomGenericViewSet(GenericViewSet):
    def get_queryset(self):
        """
        使用DataFilter过滤数据
        """
        if getattr(self, "swagger_fake_view", False):
            # queryset just for schema generation metadata
            return self.queryset.none()
        # eval_string内使用
        from django.db.models import Q  # noqa

        queryset = super().get_queryset()
        profile = self.request.user
        q_filters = profile.roles.all().values_list("data_filters__eval_string", flat=True)
        q_filter_eval_string = " | ".join(filter(bool, q_filters))  # 取或
        if q_filter_eval_string:
            return queryset.filter(eval(q_filter_eval_string))
        return queryset


class RestCreateModelMixin:
    """
    Create a model instance.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)  # noqa
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return RestResponse(data=serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    def get_success_headers(self, data):  # noqa
        try:
            return {"Location": str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}


class RestListModelMixin:
    """
    List a queryset.
    """

    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    def list(self, request, *args, **kwargs):
        simple_list = None
        simple_list_param = request.GET.get("simple_list")
        if simple_list_param:
            simple_list = simple_list_param.split(",")
            simple_list = [i.strip() for i in simple_list]
            simple_list = list(set(self.serializer_class().fields.keys()).intersection(set(simple_list)))  # noqa

        queryset = self.filter_queryset(self.get_queryset())  # noqa

        profile = request.user

        if not simple_list and not profile.is_anonymous:
            simple_list = profile.display_fields_config.get(
                self.serializer_class().Meta.model._meta.label_lower
            )  # noqa

        if simple_list:
            if "id" not in simple_list:
                simple_list.append("id")
            try:
                queryset = queryset.values(*simple_list)  # 指定字段值
            except FieldError as e:
                return RestResponse.fail(message=messages.FieldNonExists, data=repr(e))

        page = self.paginate_queryset(queryset)  # noqa
        if page is not None:
            if simple_list:
                return self.get_paginated_response(  # noqa
                    self.get_serializer(page, simple_list=simple_list, many=True).data
                )  # noqa
            serializer = self.get_serializer(page, many=True)  # noqa
            return self.get_paginated_response(serializer.data)  # noqa

        if simple_list:
            return RestResponse(data=self.get_serializer(queryset, simple_list=simple_list, many=True).data)  # noqa

        serializer = self.get_serializer(queryset, many=True)  # noqa
        return RestResponse(data=serializer.data)


class RestRetrieveModelMixin:
    """
    Retrieve a model instance.
    """

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()  # noqa
        serializer = self.get_serializer(instance)  # noqa
        return RestResponse(data=serializer.data)


class RestUpdateModelMixin:
    """
    Update a model instance.
    """

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()  # noqa
        serializer = self.get_serializer(instance, data=request.data, partial=partial)  # noqa
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return RestResponse(data=serializer.data)

    def perform_update(self, serializer):  # noqa
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class RestDestroyModelMixin:
    """
    Destroy a model instance.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # noqa
        self.perform_destroy(instance)
        return RestResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """
        直接删除, 需要保留的情况再处理。软删除唯一性校验麻烦
        """
        instance.delete()
        # instance.deleted = True
        # instance.save()


class RestModelViewSet(
    RestCreateModelMixin,
    RestRetrieveModelMixin,
    RestUpdateModelMixin,
    RestDestroyModelMixin,
    RestListModelMixin,
    CustomGenericViewSet,
):
    """
    返回 RestResponse
    """

    pass


class SerializerDictMixin:
    serializer_class_dict = {}

    def get_serializer_class(self):
        return self.serializer_class_dict.get(self.action, self.serializer_class)  # noqa
