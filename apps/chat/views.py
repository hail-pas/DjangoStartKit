from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework_jwt.serializers import jwt_payload_handler, jwt_encode_handler

from apps.account.models import Profile
from apps.chat import models, serializers
from common.drf.mixins import RestModelViewSet


def index(request):
    return render(request, "index.html")


def room(request, phone, device_code):
    user = Profile.objects.filter(phone=phone).first()
    if user:
        payload = jwt_payload_handler(user)
        return render(request, "room.html", {"device_code": device_code, "token": jwt_encode_handler(payload)})
    else:
        return render(request, "index.html")


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
