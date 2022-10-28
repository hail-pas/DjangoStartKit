"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
import sys
import logging
from pathlib import Path
from datetime import timedelta

from conf.enums import Environment
from conf.config import local_configs

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from core.restful import JSONFormatter

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-261wsap!!!du+oe#74pur=6$v8pqlm9$w42mev4h^s%)nisll5"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = local_configs.PROJECT.DEBUG
SERVER_URL = f"{local_configs.SERVER.HOST}:{local_configs.SERVER.PORT}"
PROJECT_NAME = local_configs.PROJECT.NAME
ENVIRONMENT = local_configs.PROJECT.ENVIRONMENT

# Application definition

INSTALLED_APPS = [
    # >>> 跨域
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # ===========================
    "rest_framework",  # >>> rest
    "rest_framework_jwt",
    "drf_yasg",  # >>> swagger
    "django_filters",  # >>> filter
    "captcha",
    "channels",
    # apps
    "storages.relational",
    "apis.account",
    "apis.info",
    "apis.chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # >>> 跨域
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # ===================================================
    "core.middlewares.AuthenticationMiddlewareJWT",
    "core.middlewares.ResponseProcessMiddleware",
    "core.middlewares.RequestProcessMiddleware",
]

ROOT_URLCONF = "core.urls"
AUTH_USER_MODEL = "relational.Profile"
AUTHENTICATION_BACKENDS = ["core.authenticate.CustomModelBackend"]

URI_PERMISSION_AUTHENTICATE_EXEMPT = {
    "modules": [],
    "classes": [],
    "actions": ["self"],
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = local_configs.DATABASES
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(local_configs.REDIS.HOST, local_configs.REDIS.PORT)]},
    },
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = local_configs.PROJECT.LANGUAGE_CODE

TIME_ZONE = local_configs.PROJECT.TIME_ZONE

USE_I18N = True

USE_L10N = False

USE_TZ = local_configs.PROJECT.USE_TZ

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
REQUEST_SCHEME = local_configs.SERVER.REQUEST_SCHEME
# staticfile将自动上传
# STATICFILES_STORAGE = "storages.oss.AliyunStaticStorage"
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

DATETIME_FORMAT = "Y-m-d H:i:s"

# Media files
# mediafile将自动上传
# DEFAULT_FILE_STORAGE = "storages.oss.AliyunMediaStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = False
# ==================================================================================================
# REST FRAMEWORK

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "rest_framework.permissions.DjangoModelPermissions",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_jwt.authentication.JSONWebTokenAuthentication",
        "core.restful.CsrfExemptSessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.restful.CustomPagination",
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.JSONParser",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# 跨域配置
ALLOWED_HOSTS = ["*"]
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    # 自定义头部
    "locale",  # 多语言
]

# JWT_AUTH
JWT_AUTH = {
    "JWT_AUTH_HEADER_PREFIX": local_configs.JWT.AUTH_HEADER_PREFIX,
    "JWT_RESPONSE_PAYLOAD_HANDLER": lambda token, user, request: {
        "token": token,
        "user_id": user.id,
        "username": user.username,
    },
    "JWT_SECRET_KEY": local_configs.JWT.SECRET,
    "JWT_EXPIRATION_DELTA": timedelta(minutes=local_configs.JWT.EXPIRATION_DELTA_MINUTES),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(minutes=local_configs.JWT.REFRESH_EXPIRATION_DELTA_DELTA_MINUTES),
}

if not os.path.exists(BASE_DIR.as_posix() + "/logs/error.log"):
    if not os.path.exists(BASE_DIR.as_posix() + "/logs/"):
        os.makedirs(BASE_DIR.as_posix() + "/logs/")
    os.system(f'touch {BASE_DIR.as_posix() + "/logs/error.log"}')

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {"verbose": {"()": JSONFormatter}},
    "handlers": {
        "console": {
            "level": logging.getLevelName(logging.INFO) if not DEBUG else logging.getLevelName(logging.DEBUG),
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR.as_posix() + "/logs/error.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": logging.getLevelName(logging.INFO) if not DEBUG else logging.getLevelName(logging.DEBUG),
    },
}

# Swagger Auth
SWAGGER_SETTINGS = {
    "doc_expansion": "full",
    "token_type": local_configs.JWT.AUTH_HEADER_PREFIX,
    "PERSIST_AUTH": True if local_configs.PROJECT.ENVIRONMENT == Environment.development.value else False,
    "SECURITY_DEFINITIONS": {"JWT": {"type": "apiKey", "name": "Authorization", "in": "header"}},
    "DEFAULT_AUTO_SCHEMA_CLASS": "core.restful.CustomSwaggerAutoSchema",
    "DEFAULT_GENERATOR_CLASS": "core.restful.CustomOpenAPISchemaGenerator",
}
