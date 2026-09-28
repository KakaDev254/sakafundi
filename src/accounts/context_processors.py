# accounts/context_processors.py
from django.conf import settings


def user_settings(request):
    """Add user and site settings to all templates"""
    context = {
        'site_name': 'SakaFundi',
        'site_email': settings.DEFAULT_FROM_EMAIL,
        'site_phone': getattr(settings, 'SITE_PHONE', '+254 700 123456'),
        'site_address': getattr(settings, 'SITE_ADDRESS', 'Nairobi, Kenya'),
        'currency': getattr(settings, 'CURRENCY', 'KES'),
        'currency_symbol': getattr(settings, 'CURRENCY_SYMBOL', 'KSh'),
    }

    if request.user.is_authenticated:
        context['user'] = request.user
        context['user_authenticated'] = True
        context['user_full_name'] = request.user.get_full_name()
        context['user_is_provider'] = request.user.is_provider()

        # Get wallet balance if exists
        try:
            context['wallet_balance'] = (
                request.user.wallet.balance
                if hasattr(request.user, 'wallet')
                else 0
            )
        except Exception:
            context['wallet_balance'] = 0

        # ====================================================
        # PROVIDER CONTEXT — used by navbar, profile page,
        # service listings to show the blue verified tick.
        # ====================================================
        if request.user.is_provider():
            try:
                profile = request.user.provider_profile
                context['provider_profile'] = profile
                context['is_verified_provider'] = profile.is_verified_provider
                context['provider_approximate_location'] = profile.approximate_location
                context['provider_face_verified'] = profile.face_photo_verified
                context['provider_id_verified'] = profile.id_document_verified
                context['provider_has_licence'] = profile.has_any_verified_licence()
            except Exception:
                # ProviderProfile might not exist yet (e.g. mid-registration)
                context['provider_profile'] = None
                context['is_verified_provider'] = False
                context['provider_approximate_location'] = request.user.county or 'Kenya'
                context['provider_face_verified'] = False
                context['provider_id_verified'] = False
                context['provider_has_licence'] = False
        else:
            context['provider_profile'] = None
            context['is_verified_provider'] = False

    return context