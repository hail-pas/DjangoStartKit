import logging

from apps.chat.consumers.mixins import ServerReply
from apps.chat.consumers.handler import BaseHandler

logger = logging.getLogger("chat.consumers.consumers")


class ChatConsumer(ServerReply):
    handler = BaseHandler()
