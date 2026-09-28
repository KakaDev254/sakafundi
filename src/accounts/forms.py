# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import User, ProviderProfile, KENYAN_COUNTIES


# ============================================================
# AUTH FORMS
# ============================================================

class CustomUserCreationForm(UserCreationForm):
    """Custom registration form with Kenyan phone number and email verification"""

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        validators=[
            RegexValidator(
                r'^[0-9]{9,12}$',
                'Enter a valid Kenyan phone number (e.g., 712345678)'
            )
        ],
        help_text='Enter your phone number (e.g., 712345678)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '712345678'
        })
    )

    mpesa_phone = forms.CharField(
        max_length=15,
        required=False,
        validators=[
            RegexValidator(
                r'^[0-9]{9,12}$',
                'Enter a valid M-PESA phone number (e.g., 712345678)'
            )
        ],
        help_text='M-PESA registered phone number (optional)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '712345678'
        })
    )

    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the terms and conditions'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'mpesa_phone',
            'user_type', 'password1', 'password2'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John',
                'autofocus': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Doe'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'you@email.com'
            }),
            'user_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })

        self.fields['password1'].help_text = (
            'Minimum 8 characters. Use a mix of letters, numbers, and symbols.'
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(phone_number=phone).exists():
                raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(mpesa_phone=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This M-PESA number is already registered.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.mpesa_phone = self.cleaned_data.get('mpesa_phone', '')
        user.email_verified = False

        if commit:
            user.save()
        return user


# ============================================================
# USER PROFILE FORMS
# ============================================================

class UserProfileForm(forms.ModelForm):
    """User profile update form"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'mpesa_phone',
            'bio', 'location', 'county', 'profile_image'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address',
                'readonly': True
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'mpesa_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'M-PESA phone number'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your location'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your county'
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance and self.instance.email != email:
            raise forms.ValidationError(
                'Email address cannot be changed. Contact support.'
            )
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(phone_number=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(mpesa_phone=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This M-PESA number is already registered.')
        return phone


class UserSettingsForm(forms.ModelForm):
    """User settings form"""

    class Meta:
        model = User
        fields = ['phone_number', 'mpesa_phone', 'location', 'county']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'mpesa_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'M-PESA phone number'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your location'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your county'
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(phone_number=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'

            if User.objects.filter(mpesa_phone=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This M-PESA number is already registered.')
        return phone


class ResendVerificationForm(forms.Form):
    """Form for resending verification email"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                raise forms.ValidationError('This email is already verified.')
        except User.DoesNotExist:
            raise forms.ValidationError('No account found with this email address.')
        return email


# ============================================================
# PROVIDER PROFILE FORMS — Phase 1
# ============================================================

class ProviderProfileForm(forms.ModelForm):
    """
    Edit provider face photo, ID, location, shop photo, price range.

    NOTE: This form binds to ProviderProfile (not User). The old
    User-bound version was removed — all provider-specific data
    now lives on the ProviderProfile model.
    """

    county = forms.ChoiceField(
        choices=[('', '— Select County —')] + KENYAN_COUNTIES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_county'})
    )

    class Meta:
        model = ProviderProfile
        fields = [
            'face_photo',
            'id_document',
            'id_document_type',
            'sub_county',
            'ward',
            'starting_price',
            'max_price',
            'shop_photo',
        ]
        widgets = {
            'face_photo': forms.FileInput(attrs={
                'accept': 'image/*',
                'capture': 'user'
            }),
            'id_document': forms.FileInput(attrs={'accept': 'image/*'}),
            'id_document_type': forms.Select(attrs={'class': 'form-select'}),
            'sub_county': forms.TextInput(attrs={
                'placeholder': 'e.g. Mumias',
                'class': 'form-control'
            }),
            'ward': forms.TextInput(attrs={
                'placeholder': 'Optional',
                'class': 'form-control'
            }),
            'starting_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '100'
            }),
            'max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '100'
            }),
            'shop_photo': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'face_photo': 'Face photo (no glasses, hats or filters)',
            'id_document': 'National ID or Passport (private)',
            'id_document_type': 'Document type',
            'sub_county': 'Sub-county / Town',
            'ward': 'Ward (optional)',
            'starting_price': 'Starting price (KSh)',
            'max_price': 'Typical maximum price (KSh)',
            'shop_photo': 'Photo of your shop (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['county'].initial = self.instance.user.county or ''

    def clean(self):
        cleaned = super().clean()
        sp = cleaned.get('starting_price')
        mp = cleaned.get('max_price')
        if sp and mp and mp < sp:
            raise ValidationError(
                "Maximum price can't be lower than the starting price."
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        county = self.cleaned_data.get('county')
        if county:
            instance.user.county = county
            instance.user.save(update_fields=['county'])
        if commit:
            instance.save()
        return instance


class ProviderLicenceForm(forms.ModelForm):
    """Upload licences — separate form so it doesn't block profile saves."""

    class Meta:
        model = ProviderProfile
        fields = [
            'business_licence',
            'nca_licence',
            'other_licence',
            'other_licence_name',
        ]
        widgets = {
            'business_licence': forms.FileInput(
                attrs={'accept': 'image/*,application/pdf'}
            ),
            'nca_licence': forms.FileInput(
                attrs={'accept': 'image/*,application/pdf'}
            ),
            'other_licence': forms.FileInput(
                attrs={'accept': 'image/*,application/pdf'}
            ),
            'other_licence_name': forms.TextInput(attrs={
                'placeholder': 'e.g. EPRA Licence',
                'class': 'form-control'
            }),
        }
        labels = {
            'business_licence': 'Business licence',
            'nca_licence': 'National Construction Authority licence',
            'other_licence': 'Any other professional licence',
            'other_licence_name': 'Name of the other licence',
        }