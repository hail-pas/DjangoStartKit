from rest_framework import viewsets
from rest_framework.parsers import JSONParser

from apps.account import models, serializers
from apps.permissions import SuperAdminPermission
from common.drf import RestModelViewSet


class ProfileViewSet(RestModelViewSet):
    """账号接口
    """
    serializer_class = serializers.ProfileSerializer
    queryset = models.Profile.objects.all()
    search_fields = ('phone', 'name')
    filter_fields = ('role', 'manufacturer')
    parser_classes = (JSONParser,)
    permission_classes = (SuperAdminPermission,)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.ProfileListSerializer
        return self.serializer_class
