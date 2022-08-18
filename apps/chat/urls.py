from django.urls import path, re_path
from rest_framework import routers

from apps.chat import views
from apps.chat.consumers import consumers

router = routers.SimpleRouter()
router.register("group_message", views.GroupMessageViewSet)
router.register("dialog", views.DialogViewSet)
router.register("dialog_message", views.DialogMessageViewSet)

urlpatterns = router.urls

urlpatterns += [
    path("", views.index, name="index"),
    path("<str:room_name>/", views.room, name="room"),
]

websocket_url_prefix = "websocket.chat."

websocket_urlpatterns = [
    re_path(websocket_url_prefix + r"group.(?P<identifier>\d+)$", consumers.GroupChatConsumer.as_asgi()),
    re_path(websocket_url_prefix + r"dialog.(?P<identifier>\d+)$", consumers.DialogConsumer.as_asgi()),
]
