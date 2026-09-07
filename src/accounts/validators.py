# accounts/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_kenyan_phone(value):
    """Validate Kenyan phone number format"""
    if value:
        # Remove any non-digit characters
        phone = re.sub(r'\D', '', value)
        # Check if it's 9 digits (without prefix) or 12 digits (with 254)
        if not (len(phone) == 9 or (len(phone) == 12 and phone.startswith('254'))):
            raise ValidationError(
                _('Enter a valid Kenyan phone number (e.g., 712345678 or 254712345678)')
            )
    return value


def validate_mpesa_phone(value):
    """Validate M-PESA phone number (must be Safaricom number)"""
    if value:
        phone = re.sub(r'\D', '', value)
        # M-PESA numbers typically start with 7 or 1
        if len(phone) == 9:
            if not phone.startswith(('7', '1')):
                raise ValidationError(
                    _('Enter a valid M-PESA phone number (must start with 7 or 1, e.g., 712345678)')
                )
        elif len(phone) == 12:
            if not phone.startswith('2547') and not phone.startswith('2541'):
                raise ValidationError(
                    _('Enter a valid M-PESA phone number (must start with 2547 or 2541)')
                )
    return value


def validate_id_number(value):
    """Validate Kenyan ID number"""
    if value:
        # Kenyan ID numbers are 8 digits
        if not re.match(r'^[0-9]{8}$', value):
            raise ValidationError(
                _('Enter a valid Kenyan ID number (8 digits)')
            )
    return value


def validate_kra_pin(value):
    """Validate KRA PIN format"""
    if value:
        # KRA PIN format: A123456789Z (11 characters)
        if not re.match(r'^[A-Z][0-9]{9}[A-Z]$', value):
            raise ValidationError(
                _('Enter a valid KRA PIN (e.g., A123456789Z)')
            )
    return value


def validate_kenyan_county(value):
    """Validate Kenyan county name"""
    if value:
        KENYAN_COUNTIES = [
            'baringo', 'bomet', 'bungoma', 'busia', 'elgeyo marakwet', 
            'embu', 'garissa', 'homa bay', 'isiolo', 'kajiado', 
            'kakamega', 'kericho', 'kiambu', 'kilifi', 'kirinyaga', 
            'kisii', 'kisumu', 'kitui', 'kwale', 'laikipia', 
            'lamu', 'machakos', 'makueni', 'mandera', 'marsabit', 
            'meru', 'migori', 'mombasa', 'muranga', 'nairobi', 
            'nakuru', 'nandi', 'narok', 'nyamira', 'nyandarua', 
            'nyeri', 'samburu', 'siaya', 'taita taveta', 'tana river', 
            'tharaka nithi', 'trans nzoia', 'turkana', 'uasin gishu', 
            'vihiga', 'wajir', 'west pokot'
        ]
        if value.lower() not in KENYAN_COUNTIES:
            raise ValidationError(
                _(f'Enter a valid Kenyan county name. Must be one of: {", ".join(KENYAN_COUNTIES[:10])}...')
            )
    return value