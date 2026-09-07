# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Wallet, UserNotificationPreference

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_related_objects(sender, instance, created, **kwargs):
    """Create wallet and notification preferences when user is created"""
    if created:
        # Create wallet
        Wallet.objects.get_or_create(user=instance)
        # Create notification preferences
        UserNotificationPreference.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def update_user_online_status(sender, instance, **kwargs):
    """Update user's online status when saved"""
    # You can add logic here if needed
    pass


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email to new user (optional)"""
    if created:
        # You can implement welcome email here
        pass