from django.urls import path
from rest_framework import routers

from apps.info import views

router = routers.SimpleRouter()

urlpatterns = router.urls

urlpatterns += [path("enums", views.enums)]
