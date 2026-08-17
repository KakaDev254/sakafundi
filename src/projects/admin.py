# projects/admin.py
from django.contrib import admin
from .models import (
    Project, ProjectUpdate, Dispute, ProjectMilestone, 
    ProjectDocument, ProjectActivity, ProjectInvitation
)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'provider', 'status', 'agreed_price', 'created_at')
    list_filter = ('status', 'deposit_paid', 'final_paid', 'created_at')
    search_fields = ('title', 'description', 'customer__username', 'provider__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Project Info', {
            'fields': ('title', 'description', 'requirements', 'service')
        }),
        ('People', {
            'fields': ('customer', 'provider')
        }),
        ('Pricing', {
            'fields': ('agreed_price', 'deposit_percentage', 'deposit_amount', 
                      'final_amount', 'platform_fee', 'provider_payout')
        }),
        ('Payments', {
            'fields': ('deposit_paid', 'deposit_payment_id', 'deposit_paid_at',
                      'final_paid', 'final_payment_id', 'final_paid_at')
        }),
        ('Status', {
            'fields': ('status', 'agreed_at', 'started_at', 'completed_at')
        }),
        ('Dispute', {
            'fields': ('dispute_reason', 'dispute_resolved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'type', 'content_preview', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('project__title', 'user__username', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('title', 'description', 'project__title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Dispute Info', {
            'fields': ('project', 'user', 'reason', 'title', 'description', 'attachment')
        }),
        ('Status', {
            'fields': ('status', 'resolution', 'resolved_by', 'resolved_at',
                      'admin_notes', 'is_escalated', 'escalated_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'status', 'due_date', 'is_overdue')
    list_filter = ('status', 'is_mandatory', 'due_date')
    search_fields = ('project__title', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue?'

@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'document_type', 'user', 'version', 'created_at')
    list_filter = ('document_type', 'is_latest', 'created_at')
    search_fields = ('project__title', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'activity_type', 'description', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('project__title', 'user__username', 'description')
    readonly_fields = ('created_at',)

@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = ('project', 'sender', 'recipient', 'status', 'expires_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('project__title', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at', 'updated_at')