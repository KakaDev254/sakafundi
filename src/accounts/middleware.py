# accounts/middleware.py
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AutoLogoutMiddleware:
    """Middleware that logs out inactive users after a certain time."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)  # Default 1 hour
        
    def __call__(self, request):
        # Check if user is authenticated and session exists
        if request.user.is_authenticated:
            session_time = request.session.get('login_time')
            
            if session_time:
                try:
                    login_time = timezone.datetime.fromisoformat(session_time)
                    current_time = timezone.now()
                    time_elapsed = (current_time - login_time).seconds
                    
                    # Auto logout if session has expired
                    if time_elapsed > self.timeout:
                        logout(request)
                        messages.info(request, "You have been automatically logged out due to inactivity.")
                        logger.info(f"User {request.user.email} logged out due to inactivity")
                except (ValueError, TypeError):
                    # If session time is invalid, reset it
                    pass
            
            # Update last activity for online tracking
            if request.user.is_authenticated:
                try:
                    user = request.user
                    user.update_activity()
                except AttributeError:
                    # If update_activity method doesn't exist
                    pass
        
        response = self.get_response(request)
        return response


class UserActivityMiddleware:
    """Middleware to track user activity for online status"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                request.user.update_activity()
            except AttributeError:
                pass
        
        response = self.get_response(request)
        return response


class SessionExpiryMiddleware:
    """Middleware to refresh session expiry on each request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            # Reset session expiry on each request
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            
            # Update session time
            if not request.session.get('login_time'):
                request.session['login_time'] = str(timezone.now())
        
        response = self.get_response(request)
        return response