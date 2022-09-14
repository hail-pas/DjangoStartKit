from django.urls import path, re_path
from rest_framework import routers

from apis.chat import views
from apis.chat.consumers import consumers

router = routers.SimpleRouter()
router.register("group_message", views.GroupMessageViewSet)
router.register("dialog", views.DialogViewSet)
router.register("dialog_message", views.DialogMessageViewSet)

urlpatterns = router.urls

urlpatterns += [
    path("", views.index, name="index"),
    path("online/<str:phone>/<str:device_code>/<str:chat_type>/<str:receiver_id>", views.chat_online),
]

websocket_url_prefix = "websocket."

websocket_urlpatterns = [
    re_path(websocket_url_prefix + r"chat.(?P<device_code>\w+)", consumers.ChatConsumer.as_asgi()),
]
