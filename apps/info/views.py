from drf_yasg import openapi
from rest_framework import status
from rest_framework.decorators import api_view

from apps.info import schemas
from apps.enums import get_enum_content
from apps.responses import RestResponse
from common.swagger import custom_swagger_auto_schema


@custom_swagger_auto_schema(
    tags=["info"],
    method="GET",
    query_serializer=schemas.EnumQueryIn,
    responses={
        status.HTTP_200_OK: openapi.Response(  # noqa
            description="返回Json或数组格式的Enum码表",
            examples={
                "application/json": RestResponse.ok(data={"ResponseCodeEnum": {"100200": "成功", "100999": "失败"}}).dict()
            },
        )
    },
    page_info=False,
)
@api_view(["GET"])
def enums(request, *args, **kwargs):
    """
    映射码表
    """
    return RestResponse.ok(data=get_enum_content(request.param_data["enum_name"], request.param_data["is_inversed"]))
