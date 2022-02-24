from django.db.models import QuerySet
from drf_yasg import openapi
from django.db.transaction import atomic
from drf_yasg.utils import no_body
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.viewsets import GenericViewSet

from apps import enums
from apps.account import models, serializers, schemas
from apps.permissions import SuperAdminPermission
from apps.responses import RestResponse
from common.drf.mixins import RestModelViewSet, RestListModelMixin
from common.swagger import custom_swagger_auto_schema


class ProfileViewSet(
    RestModelViewSet,
):
    """账号接口
    """
    serializer_class = serializers.ProfileSerializer
    queryset = models.Profile.objects.filter(deleted=False, is_superuser=False)
    search_fields = ('phone', 'username')
    filter_fields = ('roles', "department")
    parser_classes = (JSONParser,)
    permission_classes = (SuperAdminPermission,)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.ProfileListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return serializers.ProfileCreateUpdateSerializer
        return self.serializer_class

    @atomic
    def perform_create(self, serializer):
        roles = serializer.validated_data.get('roles')
        if models.Role.objects.filter(code=enums.RoleCodeEnum.super_admin.value).first() in roles:
            raise APIException("不能新增超级管理员")
        existed = models.Profile.objects.filter(
            phone=serializer.validated_data.get('phone')).first()  # type: models.Profile
        if existed:
            if existed.deleted:
                return RestResponse.fail(message="该账号已被归档, 可以使用后台恢复")
            else:
                return RestResponse.fail(message="具有相同手机号的用户已存在")
        operator = self.request.user  # type: models.Profile
        instance = models.Profile.objects.create(
            username=serializer.validated_data.get('username'),
            phone=serializer.validated_data.get('phone'),
            gender=serializer.validated_data.get('gender'),
            department=serializer.validated_data.get('department'),
            operator=operator
        )
        instance.set_password(instance.phone)
        instance.save(update_fields=["password"])
        if roles:
            instance.roles.add(*roles)
            for role in roles:
                instance.groups.add(*role.groups.all())

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
        roles = instance.roles.all()  # type: QuerySet
        instance.groups.clear()
        for role in roles:
            instance.groups.add(*role.groups.all())

        return RestResponse(data=serializer.data)

    @atomic
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        instance.deleted = True
        instance.operator = self.request.user
        instance.save()

    @custom_swagger_auto_schema(
        request_body=no_body,
        responses={
            status.HTTP_200_OK: openapi.Response(  # noqa
                description="",
                examples={
                    "application/json": RestResponse.ok(message="修改成功").dict()
                },

            )
        }
    )
    @action(methods=['post'], detail=True)
    def reset_password(self, request, *args, **kwargs):
        profile = self.get_object()  # type: models.Profile
        profile.set_password(profile.phone)
        profile.save()
        profile.operator = request.user
        profile.save()
        return RestResponse.ok(message="修改成功")


class RoleViewSet(
    RestModelViewSet,
):
    """
    角色接口
    """

    serializer_class = serializers.RoleSerializer
    queryset = models.Role.objects.all()
    search_fields = ('code', 'name', 'profiles__phone', 'profiles__username')
    filter_fields = ('groups', "profiles")
    parser_classes = (JSONParser,)
    permission_classes = (SuperAdminPermission,)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.RoleListSerializer
        return self.serializer_class

    @atomic
    def perform_update(self, serializer):
        instance = serializer.save()
        profiles = models.Profile.objects.filter(roles=instance)
        for p in profiles:
            p.groups.clear()
            p.groups.add(*instance.groups.all())

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # noqa
        if instance.code in enums.RoleCodeEnum.values():
            return RestResponse.fail(message="预置角色无法删除")
        if models.Profile.objects.filter(roles=instance).exists():
            return RestResponse.fail(message=f"{instance.name} 角色下还存在关联用户，禁止删除")
        instance.delete()
        return RestResponse(status=status.HTTP_204_NO_CONTENT)


class CustomizeGroupViewSet(
    RestListModelMixin,
    GenericViewSet
):
    """
    自定义菜单、权限分组接口
    """
    serializer_class = serializers.CustomizeGroupListSerializer
    queryset = models.CustomizeGroup.objects.all()
    search_fields = ('code', 'name')
    filter_fields = ('group_type', 'roles')
    parser_classes = (JSONParser,)
    permission_classes = (SuperAdminPermission,)

    @custom_swagger_auto_schema(
        operation_id="account_group_filter",
        query_serializer=schemas.CustomizeGroupQueryIn,
        responses={"200": serializers.CustomizeGroupListSerializer}
    )
    @action(methods=["GET"], detail=False)
    def filter(self, request, *args, **kwargs):
        data = request.param_data
        if data["ids"]:
            return RestResponse.ok(
                data=self.serializer_class(instance=self.queryset.filter(id__in=data["ids"].split(",")),
                                           many=True).data)
        filter_type = data["filter_type"]
        if filter_type == schemas.CustomizeGroupQueryIn.GroupFilterType.permission.value:
            return RestResponse.ok(
                data=self.serializer_class(instance=models.CustomizeGroup.permission_groups(), many=True).data)
        if filter_type == schemas.CustomizeGroupQueryIn.GroupFilterType.top_group.value:
            return RestResponse.ok(
                data=self.serializer_class(instance=models.CustomizeGroup.top_groups(), many=True).data)
        if filter_type == schemas.CustomizeGroupQueryIn.GroupFilterType.menu_level1.value:
            return RestResponse.ok(
                data=self.serializer_class(instance=models.CustomizeGroup.menu_level1_groups(), many=True).data)
        if filter_type == schemas.CustomizeGroupQueryIn.GroupFilterType.menu_level2.value:
            return RestResponse.ok(
                data=self.serializer_class(instance=models.CustomizeGroup.menu_level2_groups(), many=True).data)
        return RestResponse.fail(message="参数错误")
