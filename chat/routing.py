# chat/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<int:conversation_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/status/', consumers.StatusConsumer.as_asgi()),
]