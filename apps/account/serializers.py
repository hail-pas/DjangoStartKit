from rest_framework import serializers

from apps.account import models
from common.validators import check_mobile_phone


class CustomizeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomizeGroup
        fields = '__all__'


class CustomizeGroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomizeGroup
        fields = (
            'id',
            'parent_node_id',
            'name',
            'code',
            'group_type',
            'code',
            'order_num',
            'enabled',
        )


class ProfileSerializer(serializers.ModelSerializer):

    def validate_phone(self, value):
        if not check_mobile_phone(value):
            raise serializers.ValidationError('请正确填写手机号')
        return value

    class Meta:
        model = models.Profile
        read_only_fields = (
            'id',
            'user',
            'role_names',
            'role_codes',
            'is_active'
        )
        fields = read_only_fields + (
            'phone',
            'name',
            'roles',
        )


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Profile
        read_only_fields = (
            'id',
            'user',
            'last_login_time',
            'role_names',
            'create_time',
            'update_time',
            'is_active'
        )
        fields = read_only_fields + (
            'phone',
            'name',
            'roles',
        )
