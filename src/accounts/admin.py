# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, 
    UserBankAccount, 
    Wallet, 
    WalletTransaction,
    UserNotificationPreference,
    UserVerificationRequest,
    UserDevice,
    UserLoginHistory,
    UserSecurityLog
)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # RESTORE verification_status
    list_display = ('username', 'email', 'phone_number', 'user_type', 'verification_status', 'balance', 'is_active')
    list_filter = ('user_type', 'verification_status', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'phone_number', 'id_number', 'first_name', 'last_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Personal Info', {
            'fields': ('phone_number', 'mpesa_phone', 'profile_image', 'bio', 'location', 'county')
        }),
        ('Kenyan Details', {
            'fields': ('id_number', 'kra_pin')
        }),
        ('User Type', {
            'fields': ('user_type', 'verification_status', 'verification_notes', 'id_photo', 'verified_at')
        }),
        ('Provider Info', {
            'fields': ('skills', 'years_experience', 'rating', 'total_projects', 'completed_projects')
        }),
        ('Wallet', {
            'fields': ('balance', 'total_earned', 'total_withdrawn', 'total_spent')
        }),
    )
    
@admin.register(UserBankAccount)
class UserBankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'bank_name', 'account_name', 'account_number', 'is_default', 'is_verified')
    list_filter = ('bank_name', 'is_default', 'is_verified')
    search_fields = ('user__username', 'account_name', 'account_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_deposited', 'total_withdrawn', 'is_active')
    list_filter = ('is_active', 'is_verified')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__username', 'description', 'reference_id')
    readonly_fields = ('created_at',)

@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'push_enabled', 'in_app_enabled', 'sound_enabled')
    list_filter = ('email_enabled', 'push_enabled', 'in_app_enabled', 'sound_enabled')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserVerificationRequest)
class UserVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'request_type', 'status', 'created_at')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'document_name')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        for obj in queryset:
            obj.approve(request.user)
        self.message_user(request, f"{queryset.count()} verification request(s) approved.")
    approve_requests.short_description = "Approve selected verification requests"
    
    def reject_requests(self, request, queryset):
        for obj in queryset:
            obj.reject(request.user)
        self.message_user(request, f"{queryset.count()} verification request(s) rejected.")
    reject_requests.short_description = "Reject selected verification requests"

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'device_id', 'is_active', 'last_active')
    list_filter = ('device_type', 'is_active')
    search_fields = ('user__username', 'device_id', 'device_name')
    readonly_fields = ('created_at', 'last_active')

@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('created_at',)

@admin.register(UserSecurityLog)
class UserSecurityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'ip_address', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('created_at',)