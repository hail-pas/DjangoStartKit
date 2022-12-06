from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common import messages
from storages import enums
from storages.relational import models
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


class ProfileSimpleSerializer(CustomModelSerializer):
    is_followed = serializers.SerializerMethodField(help_text="是否已关注")

    def get_is_followed(self, obj):
        request = self.context.get("request")
        if request:
            return models.FollowRelation.objects.filter(
                followee=obj, followed=request.user.id, status=enums.Status.enable.value
            ).exists()

    class Meta:
        model = models.Profile
        fields = ["id", "avatar", "nickname", "is_followed"]


class ProfileListSerializer(CustomModelSerializer):
    class Meta:
        model = models.Profile
        fields = {"id", "is_active", "last_login", "username", "phone", "roles", "gender", "nickname", "avatar"}


class ProfileSerializer(CustomModelSerializer):
    roles = RoleSerializer(many=True)
    operator = ProfileSimpleSerializer()

    class Meta:
        model = models.Profile
        exclude = ["password", "polymorphic_ctype"]


class ProfileCreateUpdateSerializer(CustomModelSerializer):
    username = serializers.CharField(required=True, help_text="用户名", max_length=128)
    phone = serializers.CharField(
        required=True,
        help_text="手机号",
        validators=[
            UniqueValidator(queryset=models.Profile._base_manager.all(), message=messages.AccountWithPhoneExisted)
        ],
    )
    gender = serializers.ChoiceField(required=True, help_text="性别", choices=enums.GenderEnum.choices)
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
        fields = {"username", "phone", "roles", "gender", "nickname", "avatar"}


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
