from django.shortcuts import render
from rest_framework.permissions import AllowAny

from apps.chat import models, serializers
from common.drf.mixins import RestModelViewSet


def index(request):
    return render(request, "index.html")


def room(request, room_name):
    return render(request, "room.html", {"room_name": room_name})


class GroupMessageViewSet(RestModelViewSet):
    serializer_class = serializers.GroupMessageSerializer
    queryset = models.GroupMessage.objects.filter().select_related("profile")
    search_fields = ()
    filter_fields = ("profile", "group", "type")
    permission_classes = (AllowAny,)


class DialogViewSet(RestModelViewSet):
    serializer_class = serializers.DialogSerializer
    queryset = models.Dialog.objects.filter().select_related("left_user", "right_user")
    search_fields = ()
    filter_fields = (
        "left_user",
        "right_user",
    )
    permission_classes = (AllowAny,)


class DialogMessageViewSet(RestModelViewSet):
    serializer_class = serializers.DialogMessageSerializer
    queryset = models.DialogMessage.objects.filter().select_related("sender", "receiver")
    search_fields = ()
    filter_fields = ("sender", "receiver", "type", "read")
    permission_classes = (AllowAny,)
