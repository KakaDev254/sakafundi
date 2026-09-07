# accounts/views.py - Update with these changes

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from .forms import CustomUserCreationForm, UserProfileForm, ResendVerificationForm
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


# ============================================================
# REGISTER VIEW WITH EMAIL VERIFICATION
# ============================================================

def register_view(request):
    """Registration view with email verification"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Create wallet for user
            Wallet.objects.get_or_create(user=user)
            
            # Send verification email
            send_verification_email(request, user)
            
            messages.success(
                request, 
                f'Welcome {user.get_full_name()}! Please check your email to verify your account.'
            )
            return redirect('accounts:verification_sent')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


# ============================================================
# EMAIL VERIFICATION HELPER FUNCTION
# ============================================================

def send_verification_email(request, user):
    """Send verification email to user"""
    # Generate token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.id))
    
    # Build verification link
    current_site = get_current_site(request)
    verification_link = f"https://{current_site.domain}/accounts/verify-email/{uid}/{token}/"
    
    # Email subject and body
    subject = 'Verify Your Email - SakaFundi'
    html_message = render_to_string('accounts/email/verification_email.html', {
        'user': user,
        'verification_link': verification_link,
        'site_name': 'SakaFundi',
        'site_email': settings.DEFAULT_FROM_EMAIL,
    })
    plain_message = f"""
    Hello {user.get_full_name() or user.email},
    
    Welcome to SakaFundi! Please click the link below to verify your email address:
    
    {verification_link}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, please ignore this email.
    
    Regards,
    SakaFundi Team
    {settings.DEFAULT_FROM_EMAIL}
    """
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


# ============================================================
# EMAIL VERIFICATION VIEWS
# ============================================================

def verify_email_view(request, uidb64=None, token=None):
    """Verify user's email address with token"""
    if request.user.is_authenticated and request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('accounts:profile')
    
    if uidb64 and token:
        try:
            # Decode the user ID
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(User, id=user_id)
            
            # Check if token is valid
            if default_token_generator.check_token(user, token):
                user.email_verified = True
                user.save()
                
                messages.success(request, 'Your email has been verified successfully!')
                
                # Log the user in if not already
                if not request.user.is_authenticated:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Invalid or expired verification link. Please request a new one.')
                return redirect('accounts:resend_verification')
                
        except Exception as e:
            messages.error(request, 'Invalid verification link. Please request a new one.')
            return redirect('accounts:resend_verification')
    
    return render(request, 'accounts/verify_email.html')


def resend_verification(request):
    """Resend email verification link"""
    if request.user.is_authenticated and request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Send verification email
            send_verification_email(request, user)
            
            messages.success(
                request, 
                f'Verification email sent to {email}. Please check your inbox.'
            )
            return redirect('accounts:verification_sent')
    else:
        form = ResendVerificationForm()
    
    return render(request, 'accounts/resend_verification.html', {'form': form})


def verification_sent_view(request):
    """Page shown after verification email is sent"""
    return render(request, 'accounts/verification_sent.html')


# ============================================================
# CUSTOM LOGIN VIEW WITH VERIFICATION CHECK
# ============================================================

class CustomLoginView(LoginView):
    """Custom login view with email verification check"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('core:home')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password. Please try again.')
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Check if email is verified before logging in"""
        user = form.get_user()
        
        # Check if email is verified
        if not user.email_verified:
            messages.warning(
                self.request, 
                'Please verify your email address before logging in. '
                'Check your inbox for the verification link or request a new one.'
            )
            return redirect('accounts:resend_verification')
        
        # Set session expiry
        self.request.session.set_expiry(3600)  # 1 hour
        self.request.session['login_time'] = str(timezone.now())
        
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.email}!')
        return super().form_valid(form)


# ============================================================
# LOGOUT VIEW
# ============================================================

def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('core:home')


# ============================================================
# PROFILE VIEWS
# ============================================================

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
        'email_verified': user.email_verified,
        'site_email': settings.DEFAULT_FROM_EMAIL,
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
        'site_title': 'Edit Profile - SakaFundi',
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def settings_view(request):
    """User settings view"""
    if request.method == 'POST':
        user = request.user
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.location = request.POST.get('location', user.location)
        user.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('accounts:settings')
    
    context = {
        'user': request.user,
        'site_title': 'Settings - SakaFundi',
    }
    return render(request, 'accounts/settings.html', context)


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
    
    context = {
        'site_title': 'Delete Account - SakaFundi',
    }
    return render(request, 'accounts/delete_account.html', context)


# ============================================================
# WALLET VIEWS
# ============================================================

@login_required
def wallet_view(request):
    """User wallet view"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get recent transactions
    transactions = WalletTransaction.objects.filter(
        wallet=wallet
    ).order_by('-created_at')[:10]
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'site_title': 'Wallet - SakaFundi',
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
    
    context = {
        'site_title': 'Deposit - SakaFundi',
    }
    return render(request, 'accounts/wallet_deposit.html', context)


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
        'site_title': 'Withdraw - SakaFundi',
    }
    return render(request, 'accounts/wallet_withdraw.html', context)


# ============================================================
# PROVIDER VIEWS
# ============================================================

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
        'site_title': f"{provider.get_full_name()} - Provider Profile - SakaFundi",
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
    
    context = {
        'site_title': 'Become a Provider - SakaFundi',
    }
    return render(request, 'accounts/become_provider.html', context)