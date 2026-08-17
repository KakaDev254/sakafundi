# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone


class User(AbstractUser):
    """Custom User Model with Kenyan-specific fields"""
    
    USER_TYPES = (
        ('customer', 'Customer'),
        ('provider', 'Service Provider'),
        ('both', 'Both'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    # Basic Info
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='customer')
    phone_number = models.CharField(max_length=15, unique=True)
    mpesa_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Kenyan-specific
    id_number = models.CharField(max_length=20, blank=True, null=True)
    kra_pin = models.CharField(max_length=20, blank=True, null=True)
    
    # Profile
    profile_image = models.ImageField(
        upload_to='profiles/%Y/%m/', 
        default='profiles/default.jpg', 
        blank=True, 
        null=True
    )
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    county = models.CharField(max_length=50, blank=True, null=True)
    
    # Verification
    verification_status = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS, 
        default='pending'
    )
    id_photo = models.ImageField(
        upload_to='verification/%Y/%m/', 
        blank=True, 
        null=True
    )
    verification_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Provider-specific
    skills = models.JSONField(default=list, blank=True, null=True)
    years_experience = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_projects = models.IntegerField(default=0)
    completed_projects = models.IntegerField(default=0)
    
    # Wallet balance (cached from Wallet model)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.get_full_name() or self.username
    
    def get_wallet_balance(self):
        try:
            return self.wallet.balance
        except:
            return Decimal('0.00')
    
    def is_provider(self):
        return self.user_type in ['provider', 'both']
    
    def is_customer(self):
        return self.user_type in ['customer', 'both']
    
    def can_provide(self):
        return self.is_provider() and self.verification_status == 'verified'
    
    def update_rating(self):
        from reviews.models import Review
        reviews = Review.objects.filter(provider=self, is_public=True, is_hidden=False)
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(avg, 2)
            self.save()
    
    def update_stats(self):
        from projects.models import Project
        self.total_projects = Project.objects.filter(provider=self).count()
        self.completed_projects = Project.objects.filter(
            provider=self, 
            status='completed'
        ).count()
        self.save()
    
    @property
    def full_name(self):
        return self.get_full_name() or self.username


class UserBankAccount(models.Model):
    """Bank account details for withdrawals"""
    BANK_CHOICES = (
        ('equity', 'Equity Bank'),
        ('kcb', 'KCB Bank'),
        ('cooperative', 'Cooperative Bank'),
        ('absa', 'ABSA Bank'),
        ('stanbic', 'Stanbic Bank'),
        ('standard_chartered', 'Standard Chartered'),
        ('family', 'Family Bank'),
        ('ncba', 'NCBA Bank'),
        ('diamond_trust', 'Diamond Trust Bank'),
        ('gtbank', 'GTBank'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    branch = models.CharField(max_length=100, blank=True, null=True)
    branch_code = models.CharField(max_length=10, blank=True, null=True)
    swift_code = models.CharField(max_length=20, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_bank_name_display()}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            UserBankAccount.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


class Wallet(models.Model):
    """User wallet/balance"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deposited = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Limits
    daily_withdrawal_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=100000
    )
    monthly_withdrawal_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=500000
    )
    
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wallet - {self.user.username} - {self.balance}"
    
    def add_balance(self, amount, transaction_type='earning', description=''):
        self.balance += amount
        self.save()
        self.user.balance = self.balance
        self.user.save()
        
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description
        )
    
    def deduct_balance(self, amount, transaction_type='payment', description=''):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            self.user.balance = self.balance
            self.user.save()
            
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type=transaction_type,
                amount=-amount,
                balance_after=self.balance,
                description=description
            )
            return True
        return False
    
    def can_withdraw(self, amount):
        return self.balance >= amount and amount > 0 and self.is_active
    
    def get_daily_withdrawal_total(self):
        today = timezone.now().date()
        total = WalletTransaction.objects.filter(
            wallet=self,
            transaction_type='withdrawal',
            created_at__date=today
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        return abs(total)
    
    def get_monthly_withdrawal_total(self):
        first_day = timezone.now().replace(day=1)
        total = WalletTransaction.objects.filter(
            wallet=self,
            transaction_type='withdrawal',
            created_at__gte=first_day
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        return abs(total)


class WalletTransaction(models.Model):
    """Transactions for wallet"""
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('earning', 'Earning'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('fee', 'Platform Fee'),
        ('bonus', 'Bonus'),
    )
    
    wallet = models.ForeignKey(
        Wallet, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - {self.wallet.user.username} - {self.amount}"


class UserNotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences'
    )
    
    email_enabled = models.BooleanField(default=True)
    email_project_updates = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=False)
    
    push_enabled = models.BooleanField(default=True)
    push_project_updates = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=True)
    
    in_app_enabled = models.BooleanField(default=True)
    in_app_project_updates = models.BooleanField(default=True)
    in_app_messages = models.BooleanField(default=True)
    in_app_payments = models.BooleanField(default=True)
    
    sound_enabled = models.BooleanField(default=True)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class UserVerificationRequest(models.Model):
    """User verification requests"""
    REQUEST_TYPES = (
        ('id_verification', 'ID Verification'),
        ('address_verification', 'Address Verification'),
        ('professional_verification', 'Professional Verification'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_requests')
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    document = models.FileField(upload_to='verification_docs/%Y/%m/')
    document_name = models.CharField(max_length=255)
    additional_info = models.TextField(blank=True, null=True)
    
    admin_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_verifications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.request_type} - {self.status}"
    
    def approve(self, admin_user, notes=None):
        self.status = 'approved'
        self.admin_notes = notes
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
        
        if self.request_type == 'id_verification':
            self.user.verification_status = 'verified'
            self.user.verified_at = timezone.now()
            self.user.save()
    
    def reject(self, admin_user, notes=None):
        self.status = 'rejected'
        self.admin_notes = notes
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()


class UserDevice(models.Model):
    """User devices for push notifications"""
    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('desktop', 'Desktop App'),
        ('tablet', 'Tablet'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    device_id = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    registration_token = models.CharField(max_length=255)
    
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'device_id']
        ordering = ['-last_active']
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.device_name or self.device_id}"


class UserLoginHistory(models.Model):
    """User login history for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)
    is_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.created_at}"


class UserSecurityLog(models.Model):
    """Security events for users"""
    EVENT_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('password_reset', 'Password Reset'),
        ('email_change', 'Email Change'),
        ('phone_change', 'Phone Change'),
        ('profile_update', 'Profile Update'),
        ('two_factor_enable', '2FA Enable'),
        ('two_factor_disable', '2FA Disable'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_logs')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} - {self.created_at}"