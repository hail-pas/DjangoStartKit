# from django.shortcuts import render
#
# # Create your views here.
# from rest_framework import viewsets
# from rest_framework.parsers import JSONParser
# from rest_framework.permissions import IsAuthenticated
#
# from apps.account import models, serializers
# from apps.mixins import SearchFieldMixin, SimpleListMixin
#
#
# class ProfileViewSet(
#     SearchFieldMixin,
#     SimpleListMixin,
#     viewsets.ModelViewSet,
# ):
#     """账号接口
#     """
#     queryset = models.Profile.objects.all()
#     serializer_class = serializers.ProfileSerializer
#     search_fields = ('phone', 'name')
#     filter_fields = ('role', 'manufacturer')
#     parser_classes = (JSONParser,)
#     permission_classes = (IsAuthenticated, SuperAdminPermission)
#
