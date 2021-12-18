from apps.auth import views
from django.urls import path
from rest_framework import routers

router = routers.SimpleRouter()

urlpatterns = router.urls

urlpatterns += [
    path("captcha", views.CaptchaView.as_view()),
    path("login", views.LoginView.as_view()),
    path("change_pwd", views.ChangePasswordView.as_view()),
]
