# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum
from services.models import Service, ServiceCategory
from projects.models import Project
from accounts.models import User


def home(request):
    """Home page"""
    # Get featured services
    featured_services = Service.objects.filter(
        is_active=True, 
        is_featured=True
    ).select_related('provider')[:8]
    
    # Get top providers
    top_providers = User.objects.filter(
        user_type__in=['provider', 'both'],
        is_active=True
    ).order_by('-rating')[:6]
    
    # Get latest services
    latest_services = Service.objects.filter(
        is_active=True
    ).order_by('-created_at')[:8]
    
    # Get all categories for sidebar
    categories = ServiceCategory.objects.filter(is_active=True)
    
    # Stats
    total_services = Service.objects.filter(is_active=True).count()
    total_providers = User.objects.filter(
        user_type__in=['provider', 'both'],
        is_active=True
    ).count()
    completed_projects = Project.objects.filter(status='completed').count()
    
    # Average rating
    avg_rating = User.objects.filter(
        user_type__in=['provider', 'both'],
        is_active=True
    ).aggregate(Avg('rating'))['rating__avg'] or 4.8
    
    context = {
        'featured_services': featured_services,
        'top_providers': top_providers,
        'latest_services': latest_services,
        'categories': categories,
        'total_services': total_services,
        'total_providers': total_providers,
        'completed_projects': completed_projects,
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'core/home.html', context)


@login_required
def dashboard(request):
    """User dashboard"""
    user = request.user
    
    if user.is_provider():
        # Provider dashboard
        projects_as_provider = Project.objects.filter(provider=user)
        pending_projects = projects_as_provider.filter(status='deposit_paid')
        in_progress = projects_as_provider.filter(status='in_progress')
        completed = projects_as_provider.filter(status='completed')
        
        total_earnings = projects_as_provider.filter(
            status='completed'
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
        
        context = {
            'pending_projects': pending_projects.count(),
            'in_progress': in_progress.count(),
            'completed': completed.count(),
            'total_earnings': total_earnings,
            'recent_projects': projects_as_provider.order_by('-created_at')[:5],
        }
    else:
        # Customer dashboard
        projects_as_customer = Project.objects.filter(customer=user)
        active_projects = projects_as_customer.filter(
            status__in=['deposit_paid', 'in_progress']
        )
        completed = projects_as_customer.filter(status='completed')
        
        total_spent = projects_as_customer.filter(
            status='completed'
        ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0
        
        context = {
            'active_projects': active_projects.count(),
            'completed': completed.count(),
            'total_spent': total_spent,
            'recent_projects': projects_as_customer.order_by('-created_at')[:5],
        }
    
    return render(request, 'core/dashboard.html', context)


def about(request):
    """About page"""
    return render(request, 'core/about.html')


def how_it_works(request):
    """How it works page"""
    return render(request, 'core/how_it_works.html')


def terms(request):
    """Terms of Service page"""
    return render(request, 'core/terms.html')


def privacy(request):
    """Privacy Policy page"""
    return render(request, 'core/privacy.html')


def cookies(request):
    """Cookie Policy page"""
    return render(request, 'core/cookies.html')