# notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Reject anonymous users
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        # Each user gets their own group
        self.group_name = f"user_{self.scope['user'].id}"

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Client-to-server messages (optional)
        pass

    async def send_notification(self, event):
        """Push notification to the client"""
        await self.send(text_data=json.dumps({
            "type": "notification_update",
            "title": event.get("title"),
            "message": event.get("message"),
            "notification_type": event.get("notification_type", "notification"),
        }))