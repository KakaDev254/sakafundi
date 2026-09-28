# payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentMethod, PaymentTransaction, Payout


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'is_default', 'is_verified', 'created_at')
    list_filter = ('method_type', 'is_default', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number', 'account_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'payment_type', 'payment_method',
        'amount', 'status', 'is_escrow_held',
        'order_link', 'project_link', 'created_at',
    )
    list_filter = (
        'payment_type', 'payment_method', 'status',
        'is_escrow_held', 'created_at',
    )
    search_fields = (
        'user__username', 'user__email',
        'mpesa_receipt', 'mpesa_transaction_id', 'checkout_request_id',
    )
    readonly_fields = ('created_at', 'updated_at', 'escrow_released_at')

    fieldsets = (
        ('Transaction', {
            'fields': ('user', 'project', 'order', 'payment_type', 'payment_method',
                       'amount', 'platform_fee', 'net_amount')
        }),
        ('Escrow', {
            'fields': ('is_escrow_held', 'escrow_released_at'),
        }),
        ('M-PESA', {
            'fields': ('mpesa_receipt', 'mpesa_transaction_id', 'mpesa_phone', 'checkout_request_id'),
            'classes': ('collapse',),
        }),
        ('Other Providers', {
            'fields': ('stripe_payment_intent', 'stripe_client_secret',
                       'paypal_payment_id', 'paypal_payer_id'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'status_reason', 'completed_at')
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent', 'metadata',
                       'webhook_processed', 'webhook_processed_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Order')
    def order_link(self, obj):
        if obj.order_id:
            return format_html(
                '<a href="/admin/projects/order/{}/change/">Order #{}</a>',
                obj.order_id, obj.order_id
            )
        return '—'

    @admin.display(description='Project')
    def project_link(self, obj):
        if obj.project_id:
            return format_html(
                '<a href="/admin/projects/project/{}/change/">Project #{}</a>',
                obj.project_id, obj.project_id
            )
        return '—'


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'method', 'status', 'requested_at')
    list_filter = ('method', 'status', 'requested_at')
    search_fields = ('user__username', 'user__email', 'mpesa_transaction_id', 'account_number')
    readonly_fields = ('requested_at', 'processed_at', 'completed_at')