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
    fleet_labels = serializers.SerializerMethodField("get_fleet_labels")

    def get_fleet_labels(self, obj):
        return Fleet.objects.filter(id__in=obj.fleet_ids).values_list("id", "label")

    def create(self, validated_data):
        self.is_valid(raise_exception=True)
        if not validated_data.get('code'):
            codes = lazy_pinyin(validated_data['name'])
            validated_data['code'] = ''.join(codes)
        # 默认添加查看和操作元权限
        # if validated_data.get("groups"):
        #     validated_data["groups"].extend(models.CustomizeGroup.objects.filter(
        #         code__in=[enums.PermissionTypeEnum.view.value, enums.PermissionTypeEnum.operate.value]))
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
        # 默认添加查看和操作元权限
        # if validated_data.get("groups"):
        #     validated_data["groups"].extend(models.CustomizeGroup.objects.filter(
        #         code__in=[enums.PermissionTypeEnum.view.value, enums.PermissionTypeEnum.operate.value]))
        return super().update(instance, validated_data)

    def validate_province_ids(self, province_ids):
        if not isinstance(province_ids, list):
            raise ValidationError("参数格式错误, 需为ID数组")
        for province_id in province_ids:
            if not isinstance(province_id, int):
                raise ValidationError("参数格式错误, 需为ID数组")
        return province_ids

    def validate_city_ids(self, city_ids):
        if not isinstance(city_ids, list):
            raise ValidationError("参数格式错误, 需为ID数组")
        for city_id in city_ids:
            if not isinstance(city_id, int):
                raise ValidationError("参数格式错误, 需为ID数组")
        return city_ids

    def validate_fleet_ids(self, fleet_ids):
        if not isinstance(fleet_ids, list):
            raise ValidationError("参数格式错误, 需为ID数组")
        for fleet_id in fleet_ids:
            if not isinstance(fleet_id, int):
                raise ValidationError("参数格式错误, 需为ID数组")
        return fleet_ids

    class Meta:
        model = models.Role
        read_only_fields = {'id', "code", "fleet_labels"}
        fields = read_only_fields.union({
            'name',
            'groups',
            'remark',
            'province_ids',
            'city_ids',
            'fleet_ids',
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
            'department',
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
    department = serializers.ChoiceField(required=True, help_text="部门", choices=enums.DepartmentEnum.choices())
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
        fields = read_only_fields.union({"username", "phone", "gender", "department", "roles"})


class ProfileSelectSerializer(serializers.Serializer):
    profiles = serializers.PrimaryKeyRelatedField(allow_empty=False, help_text='推送用户列表', label='推送用户列表', many=True,
                                                  queryset=models.Profile.objects.all())


def get_profile_group(profile):
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
