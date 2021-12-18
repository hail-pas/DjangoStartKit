from rest_framework import serializers

from common.types import PlainSchema, StrEnumMore


class CustomizeGroupQueryIn(PlainSchema):
    class GroupFilterType(StrEnumMore):
        top_group = ("top_group", "顶级元组")
        menu_level1 = ("menu_level1", "一级菜单组")
        menu_level2 = ("menu_level2", "二级菜单组")
        permission = ("permission", "权限组")

    filter_type = serializers.ChoiceField(choices=GroupFilterType.choices(), help_text="组类别筛选", required=False,
                                          allow_null=True)
    ids = serializers.CharField(help_text="指定组id筛选, 英文逗号分隔", required=False, default=None)

    def validate(self, attrs):
        if not (attrs.get("filter_type", None) or attrs.get("ids", None)):
            raise serializers.ValidationError("必须传一个参数")
        return attrs
