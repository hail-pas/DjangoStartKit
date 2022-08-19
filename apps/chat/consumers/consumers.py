import logging

from apps.chat.consumers.mixins import ServerReply

logger = logging.getLogger("__name__")


class ChatConsumer(ServerReply):
    pass
