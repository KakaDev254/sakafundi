# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification list
    path('', views.notification_list, name='list'),
    path('all/', views.notification_list, name='all'),
    
    # Notification detail
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    
    # Mark as read/unread
    path('<int:notification_id>/mark-read/', views.mark_read, name='mark_read'),
    path('<int:notification_id>/mark-unread/', views.mark_unread, name='mark_unread'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # Delete notifications
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
    path('delete-all/', views.delete_all_notifications, name='delete_all'),
    
    # Unread count
    path('unread-count/', views.get_unread_count, name='unread_count'),
    
    # Filter notifications
    path('filter/<str:notification_type>/', views.filter_notifications, name='filter'),
    
    # Preferences
    path('preferences/', views.notification_preferences, name='preferences'),
    path('preferences/update/', views.update_preferences, name='update_preferences'),
    
    # Device registration (for push notifications)
    path('device/register/', views.register_device, name='register_device'),
    path('device/unregister/', views.unregister_device, name='unregister_device'),
]