import datetime

from drf_yasg import openapi
from drf_yasg.utils import no_body
from rest_framework import status
from django.db.transaction import atomic
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common import messages
from apis.account import serializers
from apis.responses import RestResponse
from storages.mysql import models
from apis.permissions import URIBasedPermission
from common.decorators import custom_swagger_auto_schema
from common.drf.mixins import RestModelViewSet, RestListModelMixin, CustomGenericViewSet, RestRetrieveModelMixin


class ProfileViewSet(RestModelViewSet,):
    """账号接口
    """

    serializer_class = serializers.ProfileSerializer
    queryset = models.Profile.objects.filter(delete_time__isnull=True, is_superuser=False)
    search_fields = ("phone", "username")
    filter_fields = (
        "roles",
        "gender",
    )
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated, URIBasedPermission)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.ProfileListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return serializers.ProfileCreateUpdateSerializer
        return self.serializer_class

    @atomic
    def perform_create(self, serializer):
        roles = serializer.validated_data.get("roles")
        existed = models.Profile.objects.filter(
            phone=serializer.validated_data.get("phone")
        ).first()  # type: models.Profile
        if existed:
            if existed.delete_time:
                return RestResponse.fail(message=messages.AccountArchived)
            else:
                return RestResponse.fail(message=messages.AccountWithPhoneExisted)
        operator = self.request.user  # type: models.Profile
        instance = models.Profile.objects.create(
            username=serializer.validated_data.get("username"),
            phone=serializer.validated_data.get("phone"),
            gender=serializer.validated_data.get("gender"),
            department=serializer.validated_data.get("department"),
            operator=operator,
        )
        instance.set_password(instance.phone)
        instance.save(update_fields=["password"])
        if roles:
            instance.roles.add(*roles)

    @atomic
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.delete_time = datetime.datetime.now()
        instance.operator = self.request.user
        instance.save(update_fields=["is_active", "delete_time", "operator"])

    @custom_swagger_auto_schema(
        request_body=no_body, responses={status.HTTP_200_OK: RestResponse.success_schema},
    )
    @action(methods=["post"], detail=True)
    def reset_password(self, request, *args, **kwargs):
        """
        重置密码
        """
        profile = self.get_object()  # type: models.Profile
        profile.set_password(profile.phone)
        profile.save()
        profile.operator = request.user
        profile.save()
        return RestResponse.ok(message="修改成功")

    @custom_swagger_auto_schema(query_serializer=None, responses={status.HTTP_200_OK: serializers.ProfileSerializer})
    @action(methods=["get"], detail=False, permission_classes=(IsAuthenticated,))
    def self(self, request, *args, **kwargs):
        """
        个人信息
        """
        profile = request.user  # type: models.Profile
        return RestResponse.ok(data=serializers.ProfileSerializer(instance=profile, context={"request": request}).data)


class RoleViewSet(RestModelViewSet,):
    """
    角色接口
    """

    serializer_class = serializers.RoleSerializer
    queryset = models.Role.objects.filter(delete_time__isnull=True, preserved=False)
    search_fields = ("name",)
    # filter_fields = ("",)
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated, URIBasedPermission)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.RoleListSerializer
        return self.serializer_class

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # noqa
        if models.Profile.objects.filter(roles=instance).exists():
            return RestResponse.fail(message=messages.RoleWithUsers.format(instance.name))
        instance.delete()
        return RestResponse(status=status.HTTP_204_NO_CONTENT)


class SystemResourceViewSet(RestListModelMixin, RestRetrieveModelMixin, CustomGenericViewSet):
    """
    系统资源接口
    """

    serializer_class = serializers.SystemResourceSerializer
    queryset = models.SystemResource.objects.filter(delete_time__isnull=True)
    filter_fields = ("parent", "type", "enabled")
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated, URIBasedPermission)

    def get_queryset(self):
        return self.queryset.filter(parent=None)
