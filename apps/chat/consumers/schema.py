from typing import Union, TypedDict

from apps.chat.consumers import defines


class ClientMessage(TypedDict):
    chat_type: defines.ChatType
    receiver_id: Union[str, int]
    type: defines.ClientMessage
    payload: Union[
        defines.PayloadText,
        defines.PayLoadFile,
        defines.PayloadLocation,
        defines.PayloadTyping,
        defines.PayloadStopTyping,
        defines.PayloadMessageRead,
    ]
