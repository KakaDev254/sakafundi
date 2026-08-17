# notifications/admin.py
from django.contrib import admin
from .models import Notification, NotificationDevice
# NotificationPreference removed (now in accounts)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'type', 'priority', 'is_read', 'is_expired', 'created_at')
    list_filter = ('type', 'priority', 'is_read', 'is_expired', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'type', 'priority', 'title', 'message', 'link')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_expired', 'expires_at')
        }),
        ('Actions', {
            'fields': ('action_label', 'action_url')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NotificationDevice)
class NotificationDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'device_id', 'is_active', 'last_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'device_id', 'registration_token')
    readonly_fields = ('created_at', 'updated_at')