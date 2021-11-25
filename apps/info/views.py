# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action, api_view

from apps.info import schemas
from apps.responses import RestResponse
from common.swagger import custom_swagger_auto_schema


class EnumViewSet(viewsets.ViewSet):

    @custom_swagger_auto_schema(
        tags=["info"],
        query_serializer=schemas.EnumQueryIn,
        responses={"200": schemas.EnumQueryIn(many=True)},  # RespSerializer[schemas.EnumQueryIn]
        page_info=True,
    )
    @action(methods=['get'], detail=False)
    def enums(self, request, *args, **kwargs):
        """
        docs
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return

    @custom_swagger_auto_schema(
        tags=["info"],
        query_serializer=schemas.EnumQueryIn,
        responses={"200": schemas.EnumQueryIn(many=True)},
        page_info=False,
    )
    @action(methods=['post'], detail=False)
    def enums1(self, request, *args, **kwargs):
        """
        docs
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return


@custom_swagger_auto_schema(
    method="POST",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn,
    responses={"200": schemas.EnumQueryIn},  #
    page_info=True
)
@custom_swagger_auto_schema(
    method="PUT",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn(),
    responses={"200": schemas.EnumQueryIn},
    page_info=False
)
@api_view(['POST', 'PUT'])
def example(request):
    return RestResponse(message="message")


@custom_swagger_auto_schema(
    method="POST",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn,
    responses={"200": schemas.EnumQueryIn()},  #
    page_info=False
)
@custom_swagger_auto_schema(
    method="PUT",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn(),
    responses={"200": schemas.EnumQueryIn()},
    page_info=False
)
@api_view(['POST', 'PUT'])
def example1(request):
    return RestResponse(message="message")


@custom_swagger_auto_schema(
    method="POST",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn,
    responses={"200": schemas.EnumQueryIn()},  #
    page_info=False
)
@custom_swagger_auto_schema(
    method="PUT",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn(),
    responses={"200": schemas.EnumQueryIn()},
    page_info=False
)
@api_view(['POST', 'PUT'])
def example2(request):
    return RestResponse(message="message")
