"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.http import HttpResponse
from django.urls import path, include
from django.views import static as static_view
from django.contrib import admin
from rest_framework import permissions
from django.conf.urls import url
from django.conf.urls.static import static
from rest_framework.documentation import include_docs_urls

urlpatterns = [
    path("", lambda request: HttpResponse("OK")),
    path("admin/", admin.site.urls),
    # captcha
    path("captcha/", include("captcha.urls")),
    # api
    path("auth/", include("apps.auth.urls")),
    path("info/", include("apps.info.urls")),
    path("account/", include("apps.account.urls")),
]

# Static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += [
    url(r"^static/(?P<path>.*)$", static_view.serve, {"document_root": settings.STATIC_ROOT}, name="static",),
    url(r"^media/(?P<path>.*)$", static_view.serve, {"document_root": settings.MEDIA_ROOT}, name="media"),
]

# API Docs
if settings.DEBUG:
    from drf_yasg import openapi
    from drf_yasg.views import get_schema_view

    schema_view = get_schema_view(
        openapi.Info(title="DjangoStartKit API", default_version="1.0", description="API Doc of core",),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )
    urlpatterns += [
        path(r"docs/", include_docs_urls(title="API", permission_classes=[permissions.AllowAny],)),
        url(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),  # noqa
        url(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),  # noqa
        url(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),  # noqa
    ]
