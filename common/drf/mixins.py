from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet

from apps.responses import RestResponse
from core.restful import CustomPagination


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

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
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

        queryset = self.filter_queryset(self.get_queryset())  # type: QuerySet

        if simple_list:
            queryset = queryset.values(*simple_list)  # 指定字段值

        page = self.paginate_queryset(queryset)  # noqa
        if page is not None:
            if simple_list:
                return self.get_paginated_response(page)
            serializer = self.get_serializer(page, many=True)  # noqa
            return self.get_paginated_response(serializer.data)  # noqa

        if simple_list:
            return RestResponse(data=queryset)

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
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # noqa
        serializer = self.get_serializer(instance, data=request.data, partial=partial)  # noqa
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return RestResponse(data=serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
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
        instance.delete()


class RestModelViewSet(RestCreateModelMixin,
                       RestRetrieveModelMixin,
                       RestUpdateModelMixin,
                       RestDestroyModelMixin,
                       RestListModelMixin,
                       GenericViewSet):
    """
    返回 RestResponse
    """
    pass

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            # queryset just for schema generation metadata
            return self.queryset.none()

        return super(RestModelViewSet, self).get_queryset()
