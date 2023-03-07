from drf_yasg import openapi
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.staticfiles.storage import staticfiles_storage

from apis.info import schemas
from apis.responses import RestResponse
from storages.enums import get_enum_content
from common.decorators import custom_swagger_auto_schema


class EnumsView(APIView):
    @custom_swagger_auto_schema(
        query_serializer=schemas.EnumQueryIn,
        responses={
            status.HTTP_200_OK: openapi.Response(  # noqa
                description="返回Json或数组格式的Enum码表",
                examples={
                    "application/json": RestResponse.ok(data={"ResponseCodeEnum": {"0": "成功", "200001": "失败"}}).dict()
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


class DownloadTemplateView(APIView):
    """下载模版统一接口
    """

    permission_classes = (AllowAny,)

    @custom_swagger_auto_schema(
        query_serializer=schemas.DownloadTemplateSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(  # noqa
                description="返回Json或数组格式的Enum码表",
                examples={
                    "application/json": RestResponse.ok(data={"ResponseCodeEnum": {"0": "成功", "200001": "失败"}}).dict()
                },
            )
        },
    )
    def get(self, request):
        template_name = self.request.GET.get("template_name")
        url = staticfiles_storage.url("%s.xlsx" % template_name)
        url = self.request.build_absolute_uri(url)
        return RestResponse.ok(data={"template_name": template_name, "path": url})
