from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from apps import enums
from apps.account import models
from common.validators import check_china_mobile_phone
from common.drf.serializers import CustomModelSerializer


class RoleSerializer(CustomModelSerializer):
    class Meta:
        model = models.Role
        read_only_fields = {
            "id",
        }
        fields = read_only_fields.union({"name", "remark"})


class RoleListSerializer(RoleSerializer):
    pass


class ProfileSerializer(CustomModelSerializer):
    def validate_phone(self, value):  # noqa
        if not check_china_mobile_phone(value):
            raise ValidationError("请正确填写手机号")
        return value

    class Meta:
        model = models.Profile
        read_only_fields = {
            "id",
            "is_active",
            "last_login",
            "create_time",
            "update_time",
        }
        fields = read_only_fields.union({"username", "phone", "roles", "gender"})


class ProfileListSerializer(ProfileSerializer):
    pass


class ProfileCreateUpdateSerializer(ProfileSerializer):
    username = serializers.CharField(required=True, help_text="用户名", max_length=128)
    phone = serializers.CharField(
        required=True,
        help_text="手机号",
        validators=[UniqueValidator(queryset=models.Profile._base_manager.all(), message="使用该手机号的用户已存在")],  # noqa
    )
    gender = serializers.ChoiceField(required=True, help_text="性别", choices=enums.GenderEnum.choices())
    roles = serializers.PrimaryKeyRelatedField(
        required=True,
        allow_empty=True,
        help_text="所属角色(int)",
        label="所属角色",
        many=True,
        queryset=models.Role.objects.all(),
    )

    class Meta:
        model = models.Profile
        read_only_fields = ProfileSerializer.Meta.read_only_fields
        fields = ProfileSerializer.Meta.fields


class SystemSerializer(CustomModelSerializer):
    class Meta:
        model = models.System
        fields = {
            "code",
            "label",
            "remark",
        }


class SystemResourceSerializer(CustomModelSerializer):
    children = serializers.SerializerMethodField("get_children")

    class Meta:
        model = models.SystemResource
        fields = {
            "parent",
            "label",
            "code",
            "route_path",
            "icon_path",
            "type",
            "order_num",
            "enabled",
            "children",
            "reference_to",
            "remark",
        }

    def get_children(self, obj):  # noqa
        serializer = SystemResourceSerializer(instance=obj.children, many=True)
        return serializer.data


def get_profile_system_resource(profile, instance, many: bool = True):
    system_resource_ids = profile.roles.all().values_list("system_resources__id", flat=True)

    class InnerSystemResourceSerializer(SystemResourceSerializer):
        def get_children(self, obj):  # noqa
            serializer = InnerSystemResourceSerializer(
                instance=obj.children.filter(enabled=True, id__in=system_resource_ids), many=True,
            )
            return serializer.data

    return InnerSystemResourceSerializer(instance=instance, many=many).data
