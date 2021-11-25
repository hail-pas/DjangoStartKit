from django.urls import path
from rest_framework import routers

from apps.account import views

router = routers.SimpleRouter()
router.registry("profile", views.ProfileViewSet)

urlpatterns = router.urls

urlpatterns += [
    # path(r'example', views.Example.as_view()),
]
