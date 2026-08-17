# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom registration form with Kenyan phone number"""
    
    phone_number = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                r'^[0-9]{9,12}$',
                'Enter a valid Kenyan phone number (e.g., 712345678)'
            )
        ],
        help_text='Enter your phone number (e.g., 712345678)'
    )
    
    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the terms and conditions'}
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 
                 'user_type', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Add placeholders
        self.fields['first_name'].widget.attrs.update({'placeholder': 'John'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Doe'})
        self.fields['email'].widget.attrs.update({'placeholder': 'you@email.com'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Add +254 prefix if not present
        if not phone.startswith('+'):
            phone = f'+254{phone}'
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('This phone number is already registered.')
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        user.phone_number = self.cleaned_data['phone_number']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """User profile update form"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 
                 'bio', 'location', 'county', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about yourself'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your location'}),
            'county': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your county'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }