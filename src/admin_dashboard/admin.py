# admin_dashboard/admin.py (Optional - for Django admin enhancements)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User

# Customize Django admin
admin.site.site_header = 'SakaFundi Admin'
admin.site.site_title = 'SakaFundi Admin Portal'
admin.site.index_title = 'Welcome to SakaFundi Admin'