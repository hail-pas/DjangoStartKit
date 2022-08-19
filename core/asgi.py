"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django
from channels.http import AsgiHandler
from channels.routing import ProtocolTypeRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from core.urls import websocket  # noqa

application = ProtocolTypeRouter({"http": AsgiHandler(), "websocket": websocket})
