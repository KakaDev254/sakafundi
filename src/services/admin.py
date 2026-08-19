# services/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Service, ServiceCategory, ServicePortfolio


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Service Category"""
    list_display = ('name', 'slug', 'icon_preview', 'service_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        """Display icon preview in admin list"""
        if obj.icon:
            return format_html('<i class="{}" style="font-size: 20px;"></i>', obj.icon)
        return '-'
    icon_preview.short_description = 'Icon'
    
    def service_count(self, obj):
        """Count services in this category"""
        return obj.services.filter(is_active=True).count()
    service_count.short_description = 'Services'
    
    actions = ['activate_categories', 'deactivate_categories']
    
    def activate_categories(self, request, queryset):
        """Activate selected categories"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categories activated successfully.')
    activate_categories.short_description = "Activate selected categories"
    
    def deactivate_categories(self, request, queryset):
        """Deactivate selected categories"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categories deactivated successfully.')
    deactivate_categories.short_description = "Deactivate selected categories"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Admin configuration for Services"""
    list_display = ('title', 'provider', 'category', 'price_range', 'is_active', 'is_featured', 'rating', 'orders_completed')
    list_filter = ('category', 'is_active', 'is_featured', 'created_at')
    search_fields = ('title', 'description', 'provider__username', 'provider__email')
    readonly_fields = ('views', 'rating', 'orders_completed', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Service Information', {
            'fields': ('provider', 'category', 'title', 'description')
        }),
        ('Pricing', {
            'fields': ('price_min', 'price_max', 'deposit_percentage', 'delivery_time_days')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'rating')
        }),
        ('Statistics', {
            'fields': ('views', 'orders_completed', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def price_range(self, obj):
        """Display price range"""
        return f"KSh {obj.price_min} - KSh {obj.price_max}"
    price_range.short_description = 'Price Range'
    
    actions = ['activate_services', 'deactivate_services', 'feature_services']
    
    def activate_services(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} services activated successfully.')
    activate_services.short_description = "Activate selected services"
    
    def deactivate_services(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} services deactivated successfully.')
    deactivate_services.short_description = "Deactivate selected services"
    
    def feature_services(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} services featured successfully.')
    feature_services.short_description = "Feature selected services"


@admin.register(ServicePortfolio)
class ServicePortfolioAdmin(admin.ModelAdmin):
    """Admin configuration for Service Portfolio"""
    list_display = ('service', 'title', 'is_cover', 'image_preview', 'created_at')
    list_filter = ('is_cover', 'created_at')
    search_fields = ('service__title', 'title', 'description')
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Image'