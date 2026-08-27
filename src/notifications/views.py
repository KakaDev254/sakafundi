# notifications/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.template.loader import render_to_string

from accounts.models import UserNotificationPreference  # Import from accounts
from .models import Notification, NotificationDevice
from .forms import NotificationPreferenceForm


@login_required
def notification_list(request):
    """List all notifications for the user"""
    user = request.user
    
    # Get notifications
    notifications = Notification.objects.filter(
        user=user
    ).exclude(is_expired=True)
    
    # Filter by type
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(type=notification_type)
    
    # Filter by read status
    read_status = request.GET.get('read')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Search
    query = request.GET.get('q')
    if query:
        notifications = notifications.filter(
            Q(title__icontains=query) |
            Q(message__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    
    try:
        notifications = paginator.page(page)
    except PageNotAnInteger:
        notifications = paginator.page(1)
    except EmptyPage:
        notifications = paginator.page(paginator.num_pages)
    
    # Get counts
    total_count = Notification.objects.filter(user=user).count()
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    
    # Get counts by type
    type_counts = {}
    for type_choice in Notification.NOTIFICATION_TYPES:
        type_key = type_choice[0]
        type_counts[type_key] = Notification.objects.filter(
            user=user,
            type=type_key
        ).count()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('notifications/partials/notification_list.html', {
            'notifications': notifications,
            'current_type': notification_type,
            'current_read': read_status,
            'query': query,
        }, request=request)
        return JsonResponse({'html': html, 'success': True})
    
    context = {
        'notifications': notifications,
        'total_count': total_count,
        'unread_count': unread_count,
        'type_counts': type_counts,
        'current_type': notification_type,
        'current_read': read_status,
        'query': query,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    return render(request, 'notifications/list.html', context)


@login_required
def notification_detail(request, notification_id):
    """View notification detail"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        user=request.user
    )
    
    # Mark as read if not already
    if not notification.is_read:
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    return render(request, 'notifications/detail.html', context)


@login_required
@require_POST
def mark_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        
        notification.mark_as_read()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Get updated unread count
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            return JsonResponse({
                'success': True, 
                'unread_count': unread_count,
                'message': 'Notification marked as read'
            })
        
        messages.success(request, 'Notification marked as read.')
        return redirect('notifications:list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, 'Failed to mark notification as read.')
        return redirect('notifications:list')


@login_required
@require_POST
def mark_unread(request, notification_id):
    """Mark a single notification as unread"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        
        notification.mark_as_unread()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            return JsonResponse({
                'success': True, 
                'unread_count': unread_count,
                'message': 'Notification marked as unread'
            })
        
        messages.success(request, 'Notification marked as unread.')
        return redirect('notifications:list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, 'Failed to mark notification as unread.')
        return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'marked_count': count,
                'message': f'{count} notifications marked as read'
            })
        
        messages.success(request, f'All notifications marked as read ({count} marked).')
        return redirect('notifications:list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, 'Failed to mark all as read.')
        return redirect('notifications:list')


@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        
        notification.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            return JsonResponse({
                'success': True, 
                'unread_count': unread_count,
                'message': 'Notification deleted'
            })
        
        messages.success(request, 'Notification deleted.')
        return redirect('notifications:list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, 'Failed to delete notification.')
        return redirect('notifications:list')


@login_required
@require_POST
def delete_all_notifications(request):
    """Delete all notifications"""
    try:
        count = Notification.objects.filter(user=request.user).count()
        Notification.objects.filter(user=request.user).delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'deleted_count': count,
                'message': f'{count} notifications deleted'
            })
        
        messages.success(request, f'All notifications deleted ({count} removed).')
        return redirect('notifications:list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, 'Failed to delete notifications.')
        return redirect('notifications:list')


@login_required
@require_GET
def get_unread_count(request):
    """Get unread notification count for the user"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_expired=False
        ).count()
        
        return JsonResponse({'unread_count': count, 'success': True})
    except Exception as e:
        return JsonResponse({'unread_count': 0, 'success': False, 'error': str(e)})


@login_required
@require_GET
def filter_notifications(request, notification_type):
    """Filter notifications by type"""
    return redirect(f"{reverse('notifications:list')}?type={notification_type}")


@login_required
def notification_preferences(request):
    """View and update notification preferences"""
    # Use UserNotificationPreference from accounts
    preferences, created = UserNotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully!')
            return redirect('notifications:preferences')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    context = {
        'form': form,
        'preferences': preferences,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    return render(request, 'notifications/preferences.html', context)


@login_required
@require_POST
def update_preferences(request):
    """Update notification preferences via AJAX"""
    try:
        preferences, created = UserNotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        # Get the field name and value from POST
        field_name = request.POST.get('field')
        value = request.POST.get('value')
        
        if not field_name:
            return JsonResponse({'success': False, 'error': 'Missing field name'}, status=400)
        
        if hasattr(preferences, field_name):
            # Convert string to boolean
            if value.lower() in ['true', '1', 'on']:
                value = True
            elif value.lower() in ['false', '0', 'off']:
                value = False
            
            setattr(preferences, field_name, value)
            preferences.save()
            
            return JsonResponse({
                'success': True, 
                'field': field_name, 
                'value': value,
                'message': f'Preference updated successfully'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid field'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def register_device(request):
    """Register a device for push notifications"""
    try:
        device_type = request.POST.get('device_type')
        device_id = request.POST.get('device_id')
        registration_token = request.POST.get('registration_token')
        
        if not all([device_type, device_id, registration_token]):
            return JsonResponse({
                'success': False, 
                'error': 'Missing required fields'
            }, status=400)
        
        device, created = NotificationDevice.objects.update_or_create(
            user=request.user,
            device_id=device_id,
            defaults={
                'device_type': device_type,
                'registration_token': registration_token,
                'is_active': True,
                'last_active': timezone.now()
            }
        )
        
        return JsonResponse({
            'success': True, 
            'created': created,
            'message': 'Device registered successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def unregister_device(request):
    """Unregister a device for push notifications"""
    try:
        device_id = request.POST.get('device_id')
        
        if not device_id:
            return JsonResponse({
                'success': False, 
                'error': 'Missing device_id'
            }, status=400)
        
        try:
            device = NotificationDevice.objects.get(
                user=request.user,
                device_id=device_id
            )
            device.delete()
            return JsonResponse({
                'success': True,
                'message': 'Device unregistered successfully'
            })
        except NotificationDevice.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Device not found'
            }, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ===== HELPER FUNCTIONS =====

def create_notification(user, type, title, message, link=None, priority='medium', 
                        action_label=None, action_url=None, expires_in_days=None):
    """Helper function to create a notification"""
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
    
    notification = Notification.objects.create(
        user=user,
        type=type,
        priority=priority,
        title=title,
        message=message,
        link=link,
        action_label=action_label,
        action_url=action_url,
        expires_at=expires_at
    )
    
    # Send email if enabled
    try:
        preferences = UserNotificationPreference.objects.get(user=user)
        email_field = f'email_{type}'
        if hasattr(preferences, email_field) and getattr(preferences, email_field):
            from django.core.mail import send_mail
            from django.conf import settings
            from django.template.loader import render_to_string
            
            # Email template
            subject = f"{notification.get_type_display()}: {title}"
            html_message = render_to_string('notifications/email/notification_email.html', {
                'notification': notification,
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else '',
            })
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
    except UserNotificationPreference.DoesNotExist:
        pass
    
    # Send real-time WebSocket notification
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}',
            {
                'type': 'notification_update',
                'title': title,
                'message': message,
                'notification_type': type,
                'notification_id': notification.id
            }
        )
    except Exception:
        # WebSocket not configured, silently fail
        pass
    
    return notification


def create_project_notification(user, project, title, message, link=None, **kwargs):
    """Create a project-related notification"""
    if not link:
        link = f"/projects/{project.id}/"
    
    return create_notification(
        user=user,
        type='project',
        title=title,
        message=message,
        link=link,
        **kwargs
    )


def create_payment_notification(user, amount, title, message, link=None, **kwargs):
    """Create a payment-related notification"""
    return create_notification(
        user=user,
        type='payment',
        title=title,
        message=f"{message} Amount: KSh {amount:,}",
        link=link,
        **kwargs
    )


def create_message_notification(user, sender, title, message, link=None, **kwargs):
    """Create a message-related notification"""
    if not link:
        link = f"/chat/"
    
    return create_notification(
        user=user,
        type='message',
        title=f"Message from {sender.get_full_name() or sender.username}",
        message=message[:200],
        link=link,
        **kwargs
    )


def create_dispute_notification(user, dispute, title, message, link=None, **kwargs):
    """Create a dispute-related notification"""
    if not link:
        link = f"/projects/dispute/{dispute.id}/"
    
    return create_notification(
        user=user,
        type='dispute',
        title=title,
        message=message,
        link=link,
        **kwargs
    )


def create_system_notification(user, title, message, link=None, **kwargs):
    """Create a system notification"""
    return create_notification(
        user=user,
        type='system',
        title=title,
        message=message,
        link=link,
        **kwargs
    )