import ujson
from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler

from apps.chat import models, serializers
from common.drf.mixins import RestModelViewSet
from apps.account.models import Profile


def index(request):
    return render(request, "index.html")


def chat_online(request, phone, device_code, chat_type, receiver_id):
    user = Profile.objects.filter(phone=phone).first()
    if user:
        payload = jwt_payload_handler(user)
        if chat_type == "Dialog":
            receiver = Profile.objects.filter(phone=receiver_id).first()
            if not receiver:
                return render(request, "index.html")
            receiver_id = receiver.id
        return render(
            request,
            "chat_online.html",
            {
                "profile_info": {"id": str(user.id), "nickname": user.nickname, "avatar": ""},
                "device_code": device_code,
                "token": jwt_encode_handler(payload),
                "chat_type": chat_type,
                "receiver_id": receiver_id,
            },
        )
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
