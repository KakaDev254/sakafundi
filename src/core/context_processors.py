# core/context_processors.py
from django.conf import settings

def site_settings(request):
    """Add site settings to all templates"""
    return {
        'site_name': 'SakaFundi',
        'site_description': 'Kenya\'s leading service marketplace',
        'site_email': 'info@sakafundi.com',
        'site_phone': '+254 700 123456',
        'site_address': 'Nairobi, Kenya',
        'platform_fee': settings.PLATFORM_FEE_PERCENTAGE,
        'currency': settings.CURRENCY,
        'currency_symbol': settings.CURRENCY_SYMBOL,
        'DEBUG': settings.DEBUG,
    }