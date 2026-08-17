# services/forms.py
from django import forms
from .models import Service, ServicePortfolio

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'category', 'title', 'description', 
            'price_min', 'price_max', 'deposit_percentage',
            'delivery_time_days', 'is_featured'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter service title'}),
            'price_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum price (KES)'}),
            'price_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum price (KES)'}),
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30', 'min': 0, 'max': 100}),
            'delivery_time_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Days to deliver'}),
        }
        help_texts = {
            'deposit_percentage': 'Percentage of the total price required as deposit (0-100%)',
            'delivery_time_days': 'How many days will it take to complete the work?',
        }

class ServicePortfolioForm(forms.ModelForm):
    class Meta:
        model = ServicePortfolio
        fields = ['image', 'title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image title'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Brief description'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }