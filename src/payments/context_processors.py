# payments/context_processors.py
from django.conf import settings


def fee_settings(request):
    """
    Expose platform fee percentages and currency helpers to every template.
    """
    return {
        'PLATFORM_FEE_PERCENTAGE': getattr(settings, 'PLATFORM_FEE_PERCENTAGE', 10),
        'ESCROW_SERVICE_FEE_PERCENTAGE': getattr(settings, 'ESCROW_SERVICE_FEE_PERCENTAGE', 3),
        'DEPOSIT_DEFAULT_PERCENTAGE': getattr(settings, 'DEPOSIT_DEFAULT_PERCENTAGE', 30),
        'CURRENCY': getattr(settings, 'CURRENCY', 'KES'),
        'CURRENCY_SYMBOL': getattr(settings, 'CURRENCY_SYMBOL', 'KSh'),
        'MPESA_MOCK': getattr(settings, 'MPESA_MOCK', False),
    }