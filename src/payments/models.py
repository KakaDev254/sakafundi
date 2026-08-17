# payments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from projects.models import Project

User = get_user_model()

# Wallet and WalletTransaction are now in accounts/models.py

class PaymentMethod(models.Model):
    """Payment methods for users"""
    METHOD_TYPES = (
        ('mpesa', 'M-PESA'),
        ('airtel_money', 'Airtel Money'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Wallet Balance'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    
    # M-PESA specific
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    account_name = models.CharField(max_length=200, null=True, blank=True)
    
    # Bank specific
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_branch = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    swift_code = models.CharField(max_length=20, null=True, blank=True)
    
    # Stripe/PayPal specific
    payment_provider_id = models.CharField(max_length=255, null=True, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_method_type_display()}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentTransaction(models.Model):
    """Track all payment transactions"""
    PAYMENT_TYPES = (
        ('deposit', 'Deposit'),
        ('final', 'Final Payment'),
        ('refund', 'Refund'),
        ('payout', 'Payout to Provider'),
        ('withdrawal', 'Provider Withdrawal'),
        ('wallet_deposit', 'Wallet Deposit'),
    )
    
    PAYMENT_METHODS = (
        ('mpesa', 'M-PESA'),
        ('airtel_money', 'Airtel Money'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Wallet Balance'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('reversed', 'Reversed'),
        ('cancelled', 'Cancelled'),
    )
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # M-PESA specific
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True)
    mpesa_transaction_id = models.CharField(max_length=50, null=True, blank=True)
    mpesa_phone = models.CharField(max_length=15, null=True, blank=True)
    checkout_request_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Stripe specific
    stripe_payment_intent = models.CharField(max_length=255, null=True, blank=True)
    stripe_client_secret = models.CharField(max_length=255, null=True, blank=True)
    
    # PayPal specific
    paypal_payment_id = models.CharField(max_length=255, null=True, blank=True)
    paypal_payer_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_reason = models.TextField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(null=True, blank=True)
    
    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Webhook tracking
    webhook_processed = models.BooleanField(default=False)
    webhook_processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.payment_type} - {self.user.username} - {self.amount}"


class Payout(models.Model):
    """Payouts to providers"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYOUT_METHODS = (
        ('mpesa', 'M-PESA'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYOUT_METHODS)
    
    # M-PESA specific
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    mpesa_transaction_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Bank specific
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    account_name = models.CharField(max_length=200, null=True, blank=True)
    
    # PayPal/Stripe specific
    payout_provider_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_reason = models.TextField(null=True, blank=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Payout {self.id} - {self.user.username} - {self.amount}"