# accounts/utils.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
import secrets


def send_verification_email(request, user):
    """Send email verification link to user"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    current_site = get_current_site(request)
    
    verification_link = f"https://{current_site.domain}/accounts/verify-email/{uid}/{token}/"
    
    context = {
        'user': user,
        'verification_link': verification_link,
        'site_name': 'SakaFundi',
        'site_url': f"https://{current_site.domain}",
        'site_email': settings.DEFAULT_FROM_EMAIL,
        'expiry_hours': 24,
    }
    
    subject = 'Verify Your Email - SakaFundi'
    html_message = render_to_string('accounts/email/verification_email.html', context)
    plain_message = f"""
Hello {user.get_full_name() or user.email},

Welcome to SakaFundi! Please click the link below to verify your email address:

{verification_link}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Regards,
SakaFundi Team
{settings.DEFAULT_FROM_EMAIL}
"""
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
    
    # Store when the verification was sent
    user.email_verification_sent_at = timezone.now()
    user.email_verification_token = token
    user.save()


def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Get user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')