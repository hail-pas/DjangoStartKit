# chat/consumers.py
import uuid

import ujson
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer, JsonWebsocketConsumer, AsyncWebsocketConsumer


class GroupChatConsumer(WebsocketConsumer):
    group_name = None

    def connect(self):
        self.group_name = "Group_%d" % self.scope["url_route"]["kwargs"]["group_id"]
        # Join room group
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    # def receive_json(self, content: dict, **kwargs):
    #     # 传递的参数
    #     # {
    #     #     "type": "rich_text",  # picture、video、file
    #     #     "value": ""
    #     # }
    #     # Send message to room group
    #     async_to_sync(self.channel_layer.group_send)(
    #         self.room_group_name,
    #         {
    #             'type': 'chat_message',
    #             'message': ujson.dumps(content)
    #         }
    #     )
    # Receive message from WebSocket
    def receive(self, text_data=None, bytes_data=None):
        text_data_json = ujson.loads(text_data)
        value = text_data_json["value"]

        # Send event to room group
        async_to_sync(self.channel_layer.group_send)(self.group_name, {"type": "chat_message", "value": value})

    # Receive message from room group
    def chat_message(self, event):
        value = event["value"]

        # Send message to WebSocket
        self.send(text_data=ujson.dumps({"value": value}))


class OneToOneChatConsumer(WebsocketConsumer):
    group_name = None

    def connect(self):
        self.group_name = "OneToOne_%d_%d" % (self.scope["user"].id, self.scope["url_route"]["kwargs"]["user_id"])
        # Join room group
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    # def receive_json(self, content: dict, **kwargs):
    #     # 传递的参数
    #     # {
    #     #     "type": "rich_text",  # picture、video、file
    #     #     "value": ""
    #     # }
    #     # Send message to room group
    #     async_to_sync(self.channel_layer.group_send)(
    #         self.room_group_name,
    #         {
    #             'type': 'chat_message',
    #             'message': ujson.dumps(content)
    #         }
    #     )
    # Receive message from WebSocket
    def receive(self, text_data=None, bytes_data=None):
        text_data_json = ujson.loads(text_data)
        value = text_data_json["value"]

        # Send event to room group
        async_to_sync(self.channel_layer.group_send)(self.group_name, {"type": "chat_message", "value": value})

    # Receive message from room group
    def chat_message(self, event):
        value = event["value"]

        # Send message to WebSocket
        self.send(text_data=ujson.dumps({"value": value}))


# class AsyncGroupChatConsumer(AsyncWebsocketConsumer):
#     group_name = None
#
#     async def connect(self):
#         self.group_name = 'Group_%s' % self.scope['url_route']['kwargs']['group_id']
#         # Join room group
#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )
#
#         await self.accept()
#
#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.group_name,
#             self.channel_name
#         )
#
#     # def receive_json(self, content: dict, **kwargs):
#     #     # 传递的参数
#     #     # {
#     #     #     "type": "rich_text",  # picture、video、file
#     #     #     "value": ""
#     #     # }
#     #     # Send message to room group
#     #     async_to_sync(self.channel_layer.group_send)(
#     #         self.room_group_name,
#     #         {
#     #             'type': 'chat_message',
#     #             'message': ujson.dumps(content)
#     #         }
#     #     )
#     # Receive message from WebSocket
#     async def receive(self, text_data=None, bytes_data=None):
#         text_data_json = ujson.loads(text_data)
#         value = text_data_json['value']
#
#         # Send event to room group
#         await self.channel_layer.group_send(
#             self.group_name,
#             {
#                 'type': 'chat_message',
#                 'value': value
#             }
#         )
#
#     # Receive event from room group
#     async def chat_message(self, event):
#         value = event['value']
#
#         # Send message to WebSocket
#         await self.send(text_data=ujson.dumps({
#             'value': value
#         }))
