from rest_framework import routers

from apis.account import views

router = routers.SimpleRouter()
router.register("profile", views.ProfileViewSet)
router.register("role", views.RoleViewSet)
router.register("systemResource", views.SystemResourceViewSet)

urlpatterns = router.urls

urlpatterns += []
