from .models import User

def create_user_profile(strategy, details, user=None, *args, **kwargs):
    """Create user profile after social authentication"""
    if user:
        # If user doesn't have a phone number, ask for it
        if not user.phone_number:
            # This will trigger a form in the next step
            return {
                'phone_number_required': True
            }
    return {}

def save_profile(backend, user, response, *args, **kwargs):
    """Save additional user data from social provider"""
    if backend.name == 'google-oauth2':
        # Save Google profile data
        user.email = response.get('email')
        user.first_name = response.get('given_name')
        user.last_name = response.get('family_name')
        user.save()