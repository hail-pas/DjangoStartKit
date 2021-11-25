# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action, api_view

from apps.info import schemas
from common.swagger import swagger_add_request_serializer


class EnumViewSet(viewsets.ViewSet):

    @swagger_add_request_serializer(
        tags=["info"],
        query_serializer=schemas.EnumQueryIn,
        responses={"200": {}}  # ResponseSchema.list(schemas.CompletenessRateResponseOut)
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

    @swagger_add_request_serializer(
        tags=["info"],
        query_serializer=schemas.EnumQueryIn,
        responses={"200": {}}  # ResponseSchema.list(schemas.CompletenessRateResponseOut)
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


@swagger_add_request_serializer(
    method="POST",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn,
    responses={"200": {}}  #
)
@swagger_add_request_serializer(
    method="PUT",
    tags=["info"],
    query_serializer=schemas.EnumQueryIn,
    responses={"200": {}}  #
)
@api_view(['POST', 'PUT'])
def example(request):
    return
