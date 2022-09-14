import logging

from apis.chat.consumers.mixins import ServerReply
from apis.chat.consumers.handler import BaseHandler

logger = logging.getLogger("chat.consumers.consumers")


class ChatConsumer(ServerReply):
    handler = BaseHandler()
