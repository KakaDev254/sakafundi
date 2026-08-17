# payments/forms.py
from django import forms
from .models import PaymentMethod, Payout

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['method_type', 'phone_number', 'account_name', 
                 'bank_name', 'bank_branch', 'account_number', 'swift_code']
        widgets = {
            'method_type': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '254712345678'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account holder name'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank name'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account number'}),
            'swift_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SWIFT code'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        method_type = cleaned_data.get('method_type')
        
        if method_type == 'mpesa':
            if not cleaned_data.get('phone_number'):
                self.add_error('phone_number', 'Phone number is required for M-PESA.')
        elif method_type in ['bank_transfer', 'bank_transfer']:
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', 'Bank name is required.')
            if not cleaned_data.get('account_number'):
                self.add_error('account_number', 'Account number is required.')
        
        return cleaned_data


class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = Payout
        fields = ['amount', 'method', 'phone_number', 'bank_name', 
                 'account_number', 'account_name']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 100,
                'step': 100,
                'placeholder': 'Amount in KSh'
            }),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '254712345678'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank name'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number'
            }),
            'account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name'
            }),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < 100:
            raise forms.ValidationError('Minimum withdrawal amount is KSh 100.')
        return amount


class WalletDepositForm(forms.Form):
    amount = forms.DecimalField(
        min_value=100,
        max_value=100000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount in KSh',
            'min': 100,
            'step': 100
        })
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('mpesa', 'M-PESA'),
            ('stripe', 'Stripe'),
            ('paypal', 'PayPal'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        
        if payment_method == 'mpesa' and not phone_number:
            self.add_error('phone_number', 'Phone number is required for M-PESA.')
        
        return cleaned_data


class WalletWithdrawForm(forms.Form):
    amount = forms.DecimalField(
        min_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount in KSh',
            'min': 100,
            'step': 100
        })
    )
    method = forms.ChoiceField(
        choices=[
            ('mpesa', 'M-PESA'),
            ('bank_transfer', 'Bank Transfer'),
            ('paypal', 'PayPal'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678'
        })
    )
    bank_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bank name'
        })
    )
    account_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Account number'
        })
    )
    account_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Account holder name'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('method')
        
        if method == 'mpesa':
            if not cleaned_data.get('phone_number'):
                self.add_error('phone_number', 'Phone number is required for M-PESA.')
        elif method == 'bank_transfer':
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', 'Bank name is required.')
            if not cleaned_data.get('account_number'):
                self.add_error('account_number', 'Account number is required.')
            if not cleaned_data.get('account_name'):
                self.add_error('account_name', 'Account name is required.')
        
        return cleaned_data