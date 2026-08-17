# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('settings/', views.settings_view, name='settings'),
    path('delete/', views.delete_account, name='delete_account'),
    
    # Wallet
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallet/withdraw/', views.wallet_withdraw, name='wallet_withdraw'),
    
    # Provider
    path('become-provider/', views.become_provider, name='become_provider'),
    path('provider/<int:user_id>/', views.provider_profile, name='provider_profile'),
    
    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]