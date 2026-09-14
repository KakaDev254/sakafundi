# core/context_processors.py
from django.conf import settings
from services.models import ServiceCategory


def site_settings(request):
    """Add site settings and categories to all templates"""
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

        # ✅ Only parent categories in navbar (subcategories excluded)
        'navbar_categories': ServiceCategory.objects.filter(
            is_active=True,
            parent__isnull=True
        ).prefetch_related('subcategories').order_by('order', 'name'),
    }