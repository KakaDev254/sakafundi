# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # Users
    path('users/', views.admin_users, name='users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='user_detail'),
    
    # Services
    path('services/', views.admin_services, name='services'),
    path('services/<int:service_id>/', views.admin_service_detail, name='service_detail'),
    
    # Projects
    path('projects/', views.admin_projects, name='projects'),
    path('projects/<int:project_id>/', views.admin_project_detail, name='project_detail'),
    
    # Payments
    path('payments/', views.admin_payments, name='payments'),
    
    # Disputes
    path('disputes/', views.admin_disputes, name='disputes'),
    path('disputes/<int:dispute_id>/', views.admin_dispute_detail, name='dispute_detail'),
    
    # Reviews
    path('reviews/', views.admin_reviews, name='reviews'),
    path('reviews/action/', views.admin_review_action, name='review_action'),
    
    # Bulk actions
    path('bulk-action/', views.admin_bulk_action, name='bulk_action'),
]