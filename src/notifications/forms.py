# notifications/forms.py
from django import forms
from accounts.models import UserNotificationPreference  # Import from accounts


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserNotificationPreference
        fields = [
            'email_enabled',
            'email_project_updates',
            'email_messages',
            'email_payments',
            'email_promotions',
            'push_enabled',
            'push_project_updates',
            'push_messages',
            'push_payments',
            'in_app_enabled',
            'in_app_project_updates',
            'in_app_messages',
            'in_app_payments',
            'sound_enabled',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
        ]
        widgets = {
            'quiet_hours_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'quiet_hours_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
        labels = {
            'email_enabled': 'Enable Email Notifications',
            'email_project_updates': 'Project Updates',
            'email_messages': 'New Messages',
            'email_payments': 'Payment Updates',
            'email_promotions': 'Promotions & Offers',
            'push_enabled': 'Enable Push Notifications',
            'push_project_updates': 'Project Updates',
            'push_messages': 'New Messages',
            'push_payments': 'Payment Updates',
            'in_app_enabled': 'Enable In-App Notifications',
            'in_app_project_updates': 'Project Updates',
            'in_app_messages': 'New Messages',
            'in_app_payments': 'Payment Updates',
            'sound_enabled': 'Play Sound',
            'quiet_hours_enabled': 'Enable Quiet Hours',
            'quiet_hours_start': 'Quiet Hours Start',
            'quiet_hours_end': 'Quiet Hours End',
        }
        help_texts = {
            'quiet_hours_enabled': 'Mute notifications during selected hours',
            'quiet_hours_start': 'Start time for quiet hours (24-hour format)',
            'quiet_hours_end': 'End time for quiet hours (24-hour format)',
        }