# notifications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# NotificationPreference removed (now in accounts as UserNotificationPreference)

class Notification(models.Model):
    """System notifications for users"""
    
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('payment', 'Payment'),
        ('project', 'Project'),
        ('message', 'Message'),
        ('review', 'Review'),
        ('dispute', 'Dispute'),
        ('system', 'System'),
        ('promotion', 'Promotion'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    action_label = models.CharField(max_length=50, blank=True, null=True)
    action_url = models.CharField(max_length=255, blank=True, null=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_type_display(self):
        return dict(self.NOTIFICATION_TYPES).get(self.type, self.type)
    
    def get_priority_display(self):
        return dict(self.PRIORITY_LEVELS).get(self.priority, self.priority)
    
    def get_icon(self):
        icons = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle',
            'payment': 'fa-money-bill-wave',
            'project': 'fa-briefcase',
            'message': 'fa-envelope',
            'review': 'fa-star',
            'dispute': 'fa-gavel',
            'system': 'fa-cog',
            'promotion': 'fa-gift',
        }
        return icons.get(self.type, 'fa-bell')
    
    def get_color(self):
        colors = {
            'info': 'text-primary',
            'success': 'text-success',
            'warning': 'text-warning',
            'error': 'text-danger',
            'payment': 'text-success',
            'project': 'text-primary',
            'message': 'text-info',
            'review': 'text-warning',
            'dispute': 'text-danger',
            'system': 'text-secondary',
            'promotion': 'text-success',
        }
        return colors.get(self.type, 'text-secondary')


class NotificationDevice(models.Model):
    """User devices for push notifications"""
    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('desktop', 'Desktop App'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_devices')
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    device_id = models.CharField(max_length=255)
    registration_token = models.CharField(max_length=255)
    
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'device_id']
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.device_id}"