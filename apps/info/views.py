from drf_yasg import openapi
from rest_framework import status
from rest_framework.views import APIView

from apps.info import schemas
from apps.enums import get_enum_content
from apps.responses import RestResponse
from common.swagger import custom_swagger_auto_schema
from apps.permissions import URIBasedPermission


class EnumsView(APIView):
    permission_classes = [URIBasedPermission]

    @custom_swagger_auto_schema(
        query_serializer=schemas.EnumQueryIn,
        responses={
            status.HTTP_200_OK: openapi.Response(  # noqa
                description="返回Json或数组格式的Enum码表",
                examples={
                    "application/json": RestResponse.ok(
                        data={"ResponseCodeEnum": {"100200": "成功", "100999": "失败"}}
                    ).dict()
                },
            )
        },
        page_info=False,
    )
    def get(self, request, *args, **kwargs):
        """
        获取映射码表
        """
        return RestResponse.ok(
            data=get_enum_content(request.param_data["enum_name"], request.param_data["is_reversed"])
        )
