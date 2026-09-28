# payments/context_processors.py
from django.conf import settings

def fee_settings(request):
    return {
        'PLATFORM_FEE_PERCENTAGE': settings.PLATFORM_FEE_PERCENTAGE,
        'ESCROW_SERVICE_FEE_PERCENTAGE': settings.ESCROW_SERVICE_FEE_PERCENTAGE,
        'DEPOSIT_DEFAULT_PERCENTAGE': settings.DEPOSIT_DEFAULT_PERCENTAGE,
        'CURRENCY': settings.CURRENCY,
        'CURRENCY_SYMBOL': settings.CURRENCY_SYMBOL,
    }