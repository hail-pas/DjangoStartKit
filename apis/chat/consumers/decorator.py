import logging
import functools

from apis.chat.consumers import defines

logger = logging.getLogger("apis.chat.consumers.decorators")


def authenticate_required():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            if not self.scope["user"].is_authenticated:
                logger.warning("connection rejected with unauthorized reason")
                await self.interrupt(defines.ServiceCode.Unauthorized)
            return await func(self, *args, **kwargs)

        return wrapped

    return wrapper
