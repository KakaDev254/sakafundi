# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
import base64
from django.core.files.base import ContentFile
import os
from datetime import datetime

# Don't import models at the top level - import inside methods
# from .models import Conversation, Message, ChatUserStatus, BlockedUser
# from accounts.models import User
# from notifications.models import Notification


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""
    
    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user_group_name = f'user_{self.user.id}'
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user is part of conversation
        if not await self.is_participant():
            await self.close()
            return
        
        # Check if blocked
        if await self.is_blocked():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Add user to user group (for status updates)
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user status to online
        await self.update_user_status('online', self.conversation_id)
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username,
                'status': 'online',
                'conversation_id': self.conversation_id
            }
        )
        
        # Mark messages as read when user joins
        await self.mark_messages_read()
        
        # Send recent messages
        await self.send_recent_messages()
    
    async def disconnect(self, close_code):
        # Update user status to offline
        await self.update_user_status('offline', None)
        
        # Notify others that user is offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username,
                'status': 'offline',
                'conversation_id': self.conversation_id
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Leave user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message':
            content = data.get('content', '').strip()
            attachment_data = data.get('attachment', None)
            
            if not content and not attachment_data:
                return
            
            # Check if sender is blocked
            if await self.is_blocked():
                await self.send(text_data=json.dumps({
                    'error': 'You are blocked from sending messages'
                }))
                return
            
            # Save message
            message = await self.save_message(content, attachment_data)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'content': message['content'],
                    'sender_id': self.user.id,
                    'sender_name': self.user.get_full_name() or self.user.username,
                    'sender_avatar': await self.get_user_avatar(self.user),
                    'created_at': message['created_at'],
                    'attachment_url': message['attachment_url'],
                    'attachment_name': message['attachment_name'],
                }
            )
            
            # Create notifications for other participants
            await self.create_notifications(message)
            
        elif message_type == 'typing':
            is_typing = data.get('is_typing', False)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'username': self.user.get_full_name() or self.user.username,
                    'is_typing': is_typing,
                    'conversation_id': self.conversation_id
                }
            )
        
        elif message_type == 'mark_read':
            await self.mark_messages_read()
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'user_id': self.user.id,
                    'username': self.user.get_full_name() or self.user.username
                }
            )
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event.get('sender_avatar', ''),
            'created_at': event['created_at'],
            'attachment_url': event.get('attachment_url'),
            'attachment_name': event.get('attachment_name'),
            'is_own': event['sender_id'] == self.user.id
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_status(self, event):
        """Send user status update to WebSocket"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'status': event['status']
            }))
    
    async def messages_read(self, event):
        """Send read receipts to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'user_id': event['user_id'],
            'username': event['username']
        }))
    
    @database_sync_to_async
    def is_participant(self):
        """Check if user is part of the conversation"""
        from .models import Conversation
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user,
            is_active=True
        ).exists()
    
    @database_sync_to_async
    def is_blocked(self):
        """Check if user is blocked"""
        from .models import BlockedUser, Conversation
        conversation = Conversation.objects.get(id=self.conversation_id)
        return BlockedUser.objects.filter(
            blocker=self.user,
            blocked__in=conversation.participants.all()
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content, attachment_data):
        """Save message to database"""
        from .models import Conversation, Message
        
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )
        
        # Handle attachment if provided
        attachment_url = None
        attachment_name = None
        
        if attachment_data:
            # Decode base64 attachment
            format, imgstr = attachment_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'attachment.{ext}')
            message.attachment = data
            message.attachment_name = f'attachment.{ext}'
            message.save()
            attachment_url = message.attachment.url
            attachment_name = message.attachment_name
        
        # Update conversation timestamp
        conversation.save()
        
        return {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'attachment_url': attachment_url,
            'attachment_name': attachment_name,
        }
    
    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all messages as read"""
        from .models import Conversation
        
        conversation = Conversation.objects.get(id=self.conversation_id)
        return conversation.mark_all_read(self.user)
    
    @database_sync_to_async
    def update_user_status(self, status, conversation_id):
        """Update user status"""
        from .models import ChatUserStatus
        
        status_obj, created = ChatUserStatus.objects.get_or_create(user=self.user)
        status_obj.status = status
        status_obj.last_seen = timezone.now()
        if conversation_id:
            status_obj.current_conversation_id = conversation_id
        status_obj.save()
    
    @database_sync_to_async
    def get_user_avatar(self, user):
        """Get user avatar URL"""
        if user.profile_image:
            return user.profile_image.url
        return '/static/images/default-avatar.png'
    
    @database_sync_to_async
    def create_notifications(self, message_data):
        """Create notifications for other participants"""
        from .models import Conversation
        from notifications.models import Notification
        
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        for participant in conversation.participants.exclude(id=self.user.id):
            Notification.objects.create(
                user=participant,
                type='message',
                title=f'New message from {self.user.get_full_name() or self.user.username}',
                message=message_data['content'][:200],
                link=f'/chat/conversation/{conversation.id}/'
            )
    
    @database_sync_to_async
    def get_recent_messages_data(self):
        """Get recent messages data from database"""
        from .models import Conversation
        
        conversation = Conversation.objects.get(id=self.conversation_id)
        messages = conversation.messages.select_related('sender').order_by('-created_at')[:50]
        
        message_list = []
        for msg in reversed(messages):
            message_list.append({
                'id': msg.id,
                'content': msg.content,
                'sender_id': msg.sender.id,
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'sender_avatar': self.get_user_avatar_sync(msg.sender),
                'created_at': msg.created_at.isoformat(),  # ✅ Convert to string
                'attachment_url': msg.attachment.url if msg.attachment else None,
                'attachment_name': msg.attachment_name,
                'is_own': msg.sender.id == self.user.id,
                'is_read': bool(msg.is_read)  # ✅ Ensure boolean
            })
        return message_list
    
    def get_user_avatar_sync(self, user):
        """Synchronous version of get_user_avatar for use in sync methods"""
        if user.profile_image:
            return user.profile_image.url
        return '/static/images/default-avatar.png'
    
    async def send_recent_messages(self):
        """Send recent messages to user - FIXED"""
        # Get messages data from database
        message_list = await self.get_recent_messages_data()
        
        # Send each message to the client
        for msg_data in message_list:
            # ✅ All data is now JSON serializable
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message_id': msg_data['id'],
                'content': msg_data['content'],
                'sender_id': msg_data['sender_id'],
                'sender_name': msg_data['sender_name'],
                'sender_avatar': msg_data['sender_avatar'],
                'created_at': msg_data['created_at'],  # ✅ Already string
                'attachment_url': msg_data['attachment_url'],
                'attachment_name': msg_data['attachment_name'],
                'is_own': msg_data['is_own'],
                'is_read': msg_data['is_read']  # ✅ Already boolean
            }))


class StatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for global status updates"""
    
    async def connect(self):
        self.user = self.scope['user']
        self.user_group_name = f'user_{self.user.id}'
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'status',
            'status': 'connected',
            'user_id': self.user.id
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        pass