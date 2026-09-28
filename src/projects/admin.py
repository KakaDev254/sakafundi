# projects/admin.py
from django.contrib import admin
from .models import (
    Project, ProjectUpdate, Dispute, ProjectMilestone,
    ProjectDocument, ProjectActivity, ProjectInvitation,
    Order, OrderLineItem, OrderInspiration, OrderStatusLog,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'provider', 'status', 'agreed_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'customer__email', 'provider__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'type', 'created_at')
    list_filter = ('type',)
    search_fields = ('project__title', 'user__email')


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'user', 'status', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('title', 'project__title')


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'due_date')
    list_filter = ('status',)


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'document_type', 'created_at')
    list_filter = ('document_type',)


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'activity_type', 'created_at')
    list_filter = ('activity_type',)


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = ('project', 'sender', 'recipient', 'status', 'created_at')
    list_filter = ('status',)


# ============================================================
# ORDER ADMIN — Phase 3A
# ============================================================

class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    extra = 0


class OrderInspirationInline(admin.TabularInline):
    model = OrderInspiration
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'customer', 'provider', 'status',
        'agreed_price', 'deposit_amount', 'created_at',
    )
    list_filter = (
        'status', 'materials_mode',
        'deposit_paid', 'balance_paid',
        'disclaimer_accepted',
        'created_at',
    )
    search_fields = (
        'title', 'customer__email', 'provider__email',
        'description',
    )
    readonly_fields = (
        'platform_fee', 'escrow_service_fee', 'customer_total',
        'deposit_amount', 'balance_amount', 'provider_payout',
        'created_at', 'updated_at',
    )
    inlines = [OrderLineItemInline, OrderInspirationInline]

    fieldsets = (
        ('Parties', {
            'fields': ('customer', 'provider', 'service', 'selected_sample')
        }),
        ('Job Brief', {
            'fields': ('title', 'description', 'materials_mode', 'materials_notes')
        }),
        ('Duration', {'fields': ('estimated_days',)}),
        ('Pricing', {
            'fields': (
                'agreed_price',
                'platform_fee', 'escrow_service_fee', 'customer_total',
                'deposit_percent', 'deposit_amount', 'balance_amount',
                'provider_payout',
            )
        }),
        ('Payment Tracking', {
            'fields': (
                'deposit_paid', 'deposit_payment_id', 'deposit_paid_at',
                'balance_paid', 'balance_payment_id', 'balance_paid_at',
            )
        }),
        ('Milestone', {
            'fields': ('milestone_requested_at', 'milestone_viewed_at')
        }),
        ('Status', {
            'fields': (
                'status',
                'accepted_at', 'declined_at', 'started_at',
                'submitted_at', 'completed_at', 'cancelled_at',
                'decline_reason', 'cancel_reason',
            )
        }),
        ('Disclaimers', {
            'fields': ('disclaimer_accepted', 'disclaimer_accepted_at')
        }),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    actions = ['recalculate_fees_action']

    @admin.action(description='Recalculate fees for selected orders')
    def recalculate_fees_action(self, request, queryset):
        for o in queryset:
            o.recalculate_fees()
        self.message_user(request, f'{queryset.count()} order(s) recalculated.')


@admin.register(OrderLineItem)
class OrderLineItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'title', 'quantity', 'unit', 'unit_price', 'line_total', 'provided_by')
    list_filter = ('provided_by',)
    search_fields = ('order__title', 'title')


@admin.register(OrderInspiration)
class OrderInspirationAdmin(admin.ModelAdmin):
    list_display = ('order', 'created_at')
    search_fields = ('order__title',)


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'from_status', 'to_status', 'user', 'created_at')
    list_filter = ('to_status',)
    search_fields = ('order__title',)
    readonly_fields = ('created_at',)