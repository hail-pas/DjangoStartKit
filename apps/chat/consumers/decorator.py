import functools

from apps.chat.consumers import defines


def authenticate_required():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            if not self.scope["user"].is_authenticated:
                await self.interrupt(defines.ServiceCode.Unauthorized)
            return await func(self, *args, **kwargs)

        return wrapped

    return wrapper
