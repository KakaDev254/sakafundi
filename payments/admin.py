# payments/admin.py
from django.contrib import admin
from .models import PaymentMethod, PaymentTransaction, Payout
# Wallet and WalletTransaction removed (now in accounts)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'is_default', 'is_verified', 'created_at')
    list_filter = ('method_type', 'is_default', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number', 'account_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'payment_type', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('payment_type', 'payment_method', 'status', 'created_at')
    search_fields = ('user__username', 'mpesa_receipt', 'mpesa_transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'project', 'payment_type', 'payment_method', 'amount', 'platform_fee', 'net_amount')
        }),
        ('M-PESA Details', {
            'fields': ('mpesa_receipt', 'mpesa_transaction_id', 'mpesa_phone', 'checkout_request_id'),
            'classes': ('collapse',)
        }),
        ('Stripe Details', {
            'fields': ('stripe_payment_intent', 'stripe_client_secret'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'status_reason', 'completed_at')
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'method', 'status', 'requested_at')
    list_filter = ('method', 'status', 'requested_at')
    search_fields = ('user__username', 'user__email', 'mpesa_transaction_id', 'account_number')
    readonly_fields = ('requested_at', 'processed_at', 'completed_at')
    fieldsets = (
        ('Payout Info', {
            'fields': ('user', 'amount', 'method')
        }),
        ('M-PESA Details', {
            'fields': ('phone_number', 'mpesa_transaction_id'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'account_name'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'status_reason', 'processed_at', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )