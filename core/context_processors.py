from django.conf import settings

def site_settings(request):
    """Add site settings to all templates"""
    return {
        'site_name': 'KenyaMarket',
        'site_description': 'Kenya\'s leading service marketplace',
        'platform_fee': settings.PLATFORM_FEE_PERCENTAGE,
        'currency': settings.CURRENCY,
        'currency_symbol': settings.CURRENCY_SYMBOL,
    }