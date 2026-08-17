# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('projects/', include('projects.urls')),
    path('payments/', include('payments.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls')),
    path('reviews/', include('reviews.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('admin-dashboard/', include('admin_dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)