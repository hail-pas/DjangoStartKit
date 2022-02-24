from pypinyin import lazy_pinyin
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from apps import enums
from apps.account import models
from common.drf.serializers import CustomModelSerializer
from common.validators import check_mobile_phone


class CustomizeGroupSimpleSerializer(CustomModelSerializer):
    class Meta:
        model = models.CustomizeGroup
        fields = {
            'group_type',
            'id',
            'name',
            'code',
            'path',
        }


class CustomizeGroupSerializer(CustomizeGroupSimpleSerializer):
    group_type_display = serializers.CharField(
        source='get_group_type_display',
        read_only=True,
        help_text='组类别',
    )

    class Meta:
        model = models.CustomizeGroup
        fields = CustomizeGroupSimpleSerializer.Meta.fields.union({
            'group_type',
            'group_type_display',
            'order_num',
            'enabled',
        })


class CustomizeGroupNestedSerializer(CustomizeGroupSerializer):
    subordinates = serializers.SerializerMethodField("get_subordinates")

    class Meta:
        model = models.CustomizeGroup
        fields = CustomizeGroupSerializer.Meta.fields.union({
            "subordinates",
        }) - {"group_type_display", "enabled"}  # "group_type",

    def get_subordinates(self, obj):
        items = models.CustomizeGroup.objects.filter(
            id__in=models.GroupRelation.objects.filter(parent_id=obj.id).values_list("child_id"), enabled=True)
        serializer = CustomizeGroupSimpleSerializer(instance=items, many=True)
        return serializer.data


class CustomizeGroupListSerializer(CustomizeGroupSerializer):
    subordinates = serializers.SerializerMethodField("get_subordinates")

    class Meta:
        model = models.CustomizeGroup
        fields = CustomizeGroupSerializer.Meta.fields.union({
            "subordinates",
        }) - {"group_type_display", "enabled"}  # "group_type",

    def get_subordinates(self, obj):
        items = models.CustomizeGroup.objects.filter(
            id__in=models.GroupRelation.objects.filter(parent_id=obj.id).values_list("child_id"), enabled=True)
        serializer = CustomizeGroupNestedSerializer(instance=items, many=True)
        return serializer.data


class RoleSerializer(CustomModelSerializer):

    def create(self, validated_data):
        self.is_valid(raise_exception=True)
        if not validated_data.get('code'):
            codes = lazy_pinyin(validated_data['name'])
            validated_data['code'] = ''.join(codes)
        if validated_data.get("operate_groups"):
            validated_data["operate_groups"] = list(set(validated_data["operate_groups"]))
        if validated_data.get("view_groups"):
            validated_data["view_groups"] = list(set(validated_data["view_groups"]))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.is_valid(raise_exception=True)
        if not validated_data.get('code') and validated_data.get("name"):
            codes = lazy_pinyin(validated_data['name'])
            validated_data['code'] = ''.join(codes)
        code = validated_data.get("code")
        if code in enums.RoleCodeEnum.values():
            """
            预置角色不允许修改 code 和 name
            """
            validated_data.pop("code")
            if validated_data.get("name", None):
                validated_data.pop("name")

        if validated_data.get("operate_groups"):
            validated_data["operate_groups"] = list(set(validated_data["operate_groups"]))
        if validated_data.get("view_groups"):
            validated_data["view_groups"] = list(set(validated_data["view_groups"]))
        return super().update(instance, validated_data)

    class Meta:
        model = models.Role
        read_only_fields = {'id', "code"}
        fields = read_only_fields.union({
            'name',
            'groups',
            'operate_groups',
            'view_groups',
            'remark',
        })


class RoleListSerializer(RoleSerializer):
    class Meta:
        model = models.Role
        fields = RoleSerializer.Meta.fields - {"groups"}


class ProfileSerializer(CustomModelSerializer):
    related_roles = RoleListSerializer(many=True, read_only=True)

    def validate_phone(self, value):
        if not check_mobile_phone(value):
            raise ValidationError("请正确填写手机号")
        return value

    class Meta:
        model = models.Profile
        read_only_fields = {
            'id',
            'is_active',
            'last_login',
            'related_roles',
            'create_time',
            'update_time',
        }
        fields = read_only_fields.union({
            'username',
            'phone',
            'roles',
            'gender',
        })


class ProfileListSerializer(ProfileSerializer):
    class Meta:
        model = models.Profile
        read_only_fields = ProfileSerializer.Meta.read_only_fields
        fields = ProfileSerializer.Meta.fields - {"related_roles"}


class ProfileCreateUpdateSerializer(CustomModelSerializer):
    username = serializers.CharField(required=True, help_text="用户名", max_length=128)
    phone = serializers.CharField(required=True, help_text="手机号",
                                  validators=[
                                      UniqueValidator(queryset=models.Profile._base_manager.all(),  # noqa
                                                      message="使用该手机号的用户已存在")])
    gender = serializers.ChoiceField(required=True, help_text="性别", choices=enums.GenderEnum.choices())
    roles = serializers.PrimaryKeyRelatedField(required=True, allow_empty=True, help_text='所属角色(int)', label='所属角色',
                                               many=True, queryset=models.Role.objects.all())

    def validate_phone(self, value):
        if not check_mobile_phone(value):
            raise ValidationError("请正确填写手机号")
        return value

    class Meta:
        model = models.Profile
        read_only_fields = {
            'id',
            'is_active',
            'last_login',
        }
        fields = read_only_fields.union({"username", "phone", "gender", "roles"})


class ProfileSelectSerializer(serializers.Serializer):
    profiles = serializers.PrimaryKeyRelatedField(allow_empty=False, help_text='推送用户列表', label='推送用户列表', many=True,
                                                  queryset=models.Profile.objects.all())


def get_profile_menu(profile):
    def get_subordinates(obj):
        ids = set(profile.groups.all().values_list("id", flat=True)).intersection(
            set(models.GroupRelation.objects.filter(parent=obj).values_list("child_id", flat=True)))
        items = models.CustomizeGroup.objects.filter(id__in=ids, enabled=True)
        serializer = CustomizeGroupNestedSerializer(instance=items, many=True)
        return serializer.data

    class CustomizeGroupNestedSerializer(CustomizeGroupSerializer):
        subordinates = serializers.SerializerMethodField("get_subordinates")

        class Meta:
            model = models.CustomizeGroup
            fields = CustomizeGroupSerializer.Meta.fields.union({
                "subordinates",
            }) - {"group_type_display", "enabled"}  # "group_type",

        def get_subordinates(self, obj):
            return get_subordinates(obj)

    class CustomizeGroupListFilteredSerializer(CustomizeGroupSerializer):
        subordinates = serializers.SerializerMethodField("get_subordinates")

        class Meta:
            model = models.CustomizeGroup
            fields = CustomizeGroupSerializer.Meta.fields.union({
                "subordinates",
            }) - {"group_type_display", "enabled"}  # "group_type",

        def get_subordinates(self, obj):
            return get_subordinates(obj)

    return CustomizeGroupListFilteredSerializer(
        instance=models.CustomizeGroup.menu_level1_groups() & profile.groups.filter(
            group_type=enums.GroupTypeEnum.menu.value), many=True).data
