from rest_framework import serializers

from common.types import PlainSchema
from storages.mysql import models


class ProfileSelectSerializer(PlainSchema):
    profiles = serializers.PrimaryKeyRelatedField(
        allow_empty=False, help_text="推送用户列表", label="推送用户列表", many=True, queryset=models.Profile.objects.all()
    )
