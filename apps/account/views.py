from rest_framework import viewsets
from rest_framework.parsers import JSONParser

from apps.account import models, serializers
from apps.permissions import SuperAdminPermission


class ProfileViewSet(
    viewsets.ModelViewSet,
):
    """账号接口
    """
    serializer_class = serializers.ProfileSerializer
    queryset = models.Profile.objects.all()
    search_fields = ('phone', 'name')
    filter_fields = ('role', 'manufacturer')
    parser_classes = (JSONParser,)
    permission_classes = (SuperAdminPermission,)
