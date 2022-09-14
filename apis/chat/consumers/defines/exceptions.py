from apis.chat.consumers.defines.service import Code


class ServiceException(Exception):
    def __init__(self, code: Code, message: str):
        self.code = code
        self.message = message
