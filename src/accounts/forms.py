# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from .models import User


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
        
        # Update password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Add help text for password
        self.fields['password1'].help_text = 'Minimum 8 characters. Use a mix of letters, numbers, and symbols.'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove any spaces or special characters
            phone = ''.join(filter(str.isdigit, phone))
            # Add +254 prefix if not present
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'
            
            # Check if phone already exists
            if User.objects.filter(phone_number=phone).exists():
                raise forms.ValidationError('This phone number is already registered.')
        return phone
    
    def clean_mpesa_phone(self):
        phone = self.cleaned_data.get('mpesa_phone')
        if phone:
            # Remove any spaces or special characters
            phone = ''.join(filter(str.isdigit, phone))
            # Add +254 prefix if not present
            if not phone.startswith('254') and len(phone) == 9:
                phone = f'254{phone}'
            elif not phone.startswith('+254') and len(phone) == 12:
                phone = f'+{phone}'
            elif not phone.startswith('+') and len(phone) == 12:
                phone = f'+{phone}'
            
            # Check if phone already exists (excluding current user)
            if User.objects.filter(mpesa_phone=phone).exclude(id=self.instance.id).exists():
                raise forms.ValidationError('This M-PESA number is already registered.')
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Set email as username
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.mpesa_phone = self.cleaned_data.get('mpesa_phone', '')
        
        # Email verification flag - user must verify before logging in
        user.email_verified = False
        
        if commit:
            user.save()
        return user


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
                'readonly': True  # Email cannot be changed
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
        # Prevent changing email through profile form
        if self.instance and self.instance.email != email:
            raise forms.ValidationError('Email address cannot be changed. Contact support.')
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


class ProviderProfileForm(forms.ModelForm):
    """Form for providers to update their profile"""
    
    class Meta:
        model = User
        fields = [
            'id_number', 'kra_pin', 'skills', 'years_experience',
            'bio', 'location', 'county', 'profile_image', 'id_photo'
        ]
        widgets = {
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Number'
            }),
            'kra_pin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'KRA PIN (e.g., A123456789Z)'
            }),
            'skills': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List your skills (comma separated)'
            }),
            'years_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Years of experience',
                'min': 0
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
            'id_photo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.verification_status = 'pending'  # Trigger re-verification
        if commit:
            user.save()
        return user