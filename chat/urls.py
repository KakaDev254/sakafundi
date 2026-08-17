# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat list
    path('', views.chat_list, name='list'),
    path('conversations/', views.chat_list, name='conversations'),
    
    # Conversation management
    path('conversation/<int:conversation_id>/', views.chat_detail, name='detail'),
    path('conversation/<int:conversation_id>/delete/', views.delete_conversation, name='delete'),
    path('conversation/<int:conversation_id>/leave/', views.leave_conversation, name='leave'),
    
    # Messages (fallback for non-WebSocket)
    path('conversation/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('conversation/<int:conversation_id>/mark-read/', views.mark_read, name='mark_read'),
    
    # Start new conversation
    path('start/', views.start_conversation, name='start'),
    path('start/<int:user_id>/', views.start_conversation_with_user, name='start_with_user'),
    path('start-from-project/<int:project_id>/', views.start_from_project, name='start_from_project'),
    
    # Notifications
    path('unread-count/', views.get_unread_count, name='unread_count'),
    path('unread-messages/', views.get_unread_messages, name='unread_messages'),
    
    # Attachments
    path('attachment/<int:message_id>/', views.view_attachment, name='view_attachment'),
    path('attachment/<int:message_id>/download/', views.download_attachment, name='download_attachment'),
    
    # Search
    path('search/', views.search_conversations, name='search'),
    path('search-users/', views.search_users, name='search_users'),
    
    # Block/Unblock
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
]