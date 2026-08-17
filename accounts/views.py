# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from .forms import CustomUserCreationForm, UserProfileForm
from .models import (
    User, 
    Wallet, 
    WalletTransaction,
    UserNotificationPreference,
    UserBankAccount,
    UserVerificationRequest,
    UserDevice
)
from services.models import Service
from projects.models import Project
from reviews.models import Review


def register_view(request):
    """Modern registration view"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Fix: Pass the backend explicitly
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Create wallet for user
            Wallet.objects.get_or_create(user=user)
            
            messages.success(request, f'Welcome {user.get_full_name()}! Your account has been created.')
            
            if user.user_type == 'provider':
                return redirect('services:create')
            return redirect('core:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('core:home')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)


def logout_view(request):
    """Logout user"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


@login_required
def profile_view(request):
    """User profile view"""
    user = request.user
    
    # Get user stats
    if user.is_provider():
        total_services = Service.objects.filter(provider=user, is_active=True).count()
        total_projects = Project.objects.filter(provider=user).count()
        completed_projects = Project.objects.filter(provider=user, status='completed').count()
        total_reviews = Review.objects.filter(provider=user).count()
    else:
        total_services = 0
        total_projects = Project.objects.filter(customer=user).count()
        completed_projects = Project.objects.filter(customer=user, status='completed').count()
        total_reviews = Review.objects.filter(customer=user).count()
    
    context = {
        'user': user,
        'total_services': total_services,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'total_reviews': total_reviews,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def wallet_view(request):
    """User wallet view"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get recent transactions
    transactions = WalletTransaction.objects.filter(
        wallet=wallet
    ).order_by('-created_at')[:10]
    
    # Get stats
    total_deposited = wallet.total_deposited
    total_withdrawn = wallet.total_withdrawn
    total_earned = wallet.total_earned
    total_spent = wallet.total_spent
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
        'total_earned': total_earned,
        'total_spent': total_spent,
    }
    return render(request, 'accounts/wallet.html', context)


@login_required
def wallet_deposit(request):
    """Deposit money to wallet"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        
        if amount and float(amount) > 0:
            messages.success(request, f'Deposit of KSh {amount} initiated successfully!')
            return redirect('accounts:wallet')
        else:
            messages.error(request, 'Invalid amount specified.')
    
    return render(request, 'accounts/wallet_deposit.html')


@login_required
def wallet_withdraw(request):
    """Withdraw money from wallet"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        
        if amount and float(amount) > 0:
            if wallet.balance >= float(amount):
                messages.success(request, f'Withdrawal of KSh {amount} initiated successfully!')
                return redirect('accounts:wallet')
            else:
                messages.error(request, 'Insufficient balance.')
        else:
            messages.error(request, 'Invalid amount specified.')
    
    context = {
        'wallet': wallet,
        'max_amount': wallet.balance,
    }
    return render(request, 'accounts/wallet_withdraw.html', context)


def provider_profile(request, user_id):
    """View provider profile"""
    provider = get_object_or_404(User, id=user_id, is_active=True)
    
    if not provider.is_provider():
        messages.error(request, 'This user is not a service provider.')
        return redirect('core:home')
    
    services = Service.objects.filter(provider=provider, is_active=True)
    reviews = Review.objects.filter(
        provider=provider,
        is_public=True,
        is_hidden=False
    ).order_by('-created_at')[:10]
    
    total_services = services.count()
    total_reviews = Review.objects.filter(provider=provider, is_public=True).count()
    completed_projects = Project.objects.filter(provider=provider, status='completed').count()
    
    rating_distribution = {
        '5': Review.objects.filter(provider=provider, rating=5, is_public=True).count(),
        '4': Review.objects.filter(provider=provider, rating=4, is_public=True).count(),
        '3': Review.objects.filter(provider=provider, rating=3, is_public=True).count(),
        '2': Review.objects.filter(provider=provider, rating=2, is_public=True).count(),
        '1': Review.objects.filter(provider=provider, rating=1, is_public=True).count(),
    }
    
    context = {
        'provider': provider,
        'services': services,
        'reviews': reviews,
        'total_services': total_services,
        'total_reviews': total_reviews,
        'completed_projects': completed_projects,
        'rating_distribution': rating_distribution,
        'can_review': request.user.is_authenticated and request.user != provider,
    }
    return render(request, 'accounts/provider_profile.html', context)


@login_required
def become_provider(request):
    """Become a provider view"""
    if request.user.is_provider():
        messages.info(request, 'You are already a provider.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        user = request.user
        user.user_type = 'provider'
        user.save()
        messages.success(request, 'You are now a provider! You can start adding services.')
        return redirect('services:create')
    
    return render(request, 'accounts/become_provider.html')


@login_required
def settings_view(request):
    """User settings view"""
    if request.method == 'POST':
        user = request.user
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('accounts:settings')
    
    return render(request, 'accounts/settings.html', {'user': request.user})


@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        user = request.user
        user.is_active = False
        user.save()
        logout(request)
        messages.success(request, 'Your account has been deactivated.')
        return redirect('core:home')
    
    return render(request, 'accounts/delete_account.html')