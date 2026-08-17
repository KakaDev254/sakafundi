# reviews/admin.py
from django.contrib import admin
from .models import Review, ReviewHelpful, ReviewReport, ReviewCategory

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'customer', 'rating', 'title', 'is_verified', 'is_public', 'created_at')
    list_filter = ('rating', 'is_verified', 'is_public', 'is_hidden', 'created_at')
    search_fields = ('provider__username', 'customer__username', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count', 'unhelpful_count')
    
    fieldsets = (
        ('Review Info', {
            'fields': ('provider', 'customer', 'project', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_public', 'is_verified', 'is_hidden', 'is_reported', 
                      'hidden_reason', 'admin_notes')
        }),
        ('Helpful Votes', {
            'fields': ('helpful_count', 'unhelpful_count')
        }),
        ('Response', {
            'fields': ('response', 'response_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = ('review__title', 'user__username')

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'created_at')
    search_fields = ('review__title', 'user__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['mark_reviewed', 'mark_actioned', 'mark_dismissed']
    
    def mark_reviewed(self, request, queryset):
        queryset.update(status='reviewed')
    mark_reviewed.short_description = 'Mark as Reviewed'
    
    def mark_actioned(self, request, queryset):
        queryset.update(status='actioned')
    mark_actioned.short_description = 'Mark as Action Taken'
    
    def mark_dismissed(self, request, queryset):
        queryset.update(status='dismissed')
    mark_dismissed.short_description = 'Mark as Dismissed'

@admin.register(ReviewCategory)
class ReviewCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}