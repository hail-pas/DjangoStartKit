from django.urls import path
from rest_framework import routers

from apps.info import views

router = routers.SimpleRouter()

router.register(r'enum', views.EnumViewSet, basename="enum")

urlpatterns = router.urls

urlpatterns += [
    path(r'example', views.example),
    path(r'example1', views.example1), path(r'example2', views.example2),
]
