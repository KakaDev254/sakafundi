# accounts/context_processors.py
from django.conf import settings


def user_settings(request):
    """Add user and site settings to all templates"""
    context = {
        'site_name': 'SakaFundi',
        'site_email': settings.DEFAULT_FROM_EMAIL,
        'site_phone': '+254 700 123456',
        'site_address': 'Nairobi, Kenya',
        'currency': 'KES',
        'currency_symbol': 'KSh',
    }
    
    if request.user.is_authenticated:
        context['user'] = request.user
        context['user_authenticated'] = True
        context['user_full_name'] = request.user.get_full_name()
        context['user_is_provider'] = request.user.is_provider()
        
        # Get wallet balance if exists
        try:
            context['wallet_balance'] = request.user.wallet.balance if hasattr(request.user, 'wallet') else 0
        except:
            context['wallet_balance'] = 0
    
    return context