# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.models import User, Wallet
from services.models import Service
from projects.models import Project, ProjectActivity
from reviews.models import Review
from chat.models import Conversation, Message
from notifications.models import Notification


@login_required
def dashboard_home(request):
    """Main dashboard view"""
    user = request.user
    
    if user.is_provider():
        context = get_provider_dashboard_data(request)
        template = 'dashboard/provider_dashboard.html'
    else:
        context = get_customer_dashboard_data(request)
        template = 'dashboard/customer_dashboard.html'
    
    context['user'] = user
    context['today'] = timezone.now()
    context['is_provider'] = user.is_provider()
    
    return render(request, template, context)


def get_provider_dashboard_data(request):
    """Get data for provider dashboard"""
    user = request.user
    
    # Stats Cards
    total_projects = Project.objects.filter(provider=user).count()
    completed_projects = Project.objects.filter(provider=user, status='completed').count()
    pending_projects = Project.objects.filter(
        provider=user,
        status__in=['deposit_paid', 'in_progress', 'submitted']
    ).count()
    
    total_earnings = Project.objects.filter(
        provider=user,
        status='completed'
    ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
    
    total_services = Service.objects.filter(provider=user, is_active=True).count()
    total_views = Service.objects.filter(provider=user).aggregate(Sum('views'))['views__sum'] or 0
    total_reviews = Review.objects.filter(provider=user).count()
    avg_rating = Review.objects.filter(provider=user).aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Unread counts
    conversations = Conversation.objects.filter(participants=user)
    unread_messages = Message.objects.filter(
        conversation__in=conversations,
        is_read=False
    ).exclude(sender=user).count()
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
    
    # Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)
    
    stats = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'pending_projects': pending_projects,
        'total_earnings': total_earnings,
        'total_services': total_services,
        'total_views': total_views,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'unread_messages': unread_messages,
        'unread_notifications': unread_notifications,
        'wallet_balance': wallet.balance,
    }
    
    # Earnings Chart Data (Last 30 days)
    earnings_data = get_earnings_chart_data(user)
    
    # Recent Projects
    recent_projects = Project.objects.filter(
        provider=user
    ).select_related('customer', 'service').order_by('-created_at')[:5]
    
    # Status Distribution
    status_distribution = {
        'negotiating': Project.objects.filter(provider=user, status='negotiating').count(),
        'agreed': Project.objects.filter(provider=user, status='agreed').count(),
        'deposit_paid': Project.objects.filter(provider=user, status='deposit_paid').count(),
        'in_progress': Project.objects.filter(provider=user, status='in_progress').count(),
        'submitted': Project.objects.filter(provider=user, status='submitted').count(),
        'completed': Project.objects.filter(provider=user, status='completed').count(),
        'disputed': Project.objects.filter(provider=user, status='disputed').count(),
        'cancelled': Project.objects.filter(provider=user, status='cancelled').count(),
    }
    
    # Recent Reviews
    recent_reviews = Review.objects.filter(
        provider=user
    ).select_related('customer').order_by('-created_at')[:5]
    
    # Recent Activities
    recent_activities = ProjectActivity.objects.filter(
        project__provider=user
    ).select_related('project', 'user').order_by('-created_at')[:10]
    
    # Monthly Performance
    monthly_data = get_monthly_performance(user)
    
    context = {
        'stats': stats,
        'earnings_data': earnings_data,
        'recent_projects': recent_projects,
        'status_distribution': status_distribution,
        'recent_reviews': recent_reviews,
        'recent_activities': recent_activities,
        'monthly_data': monthly_data,
    }
    
    return context


def get_customer_dashboard_data(request):
    """Get data for customer dashboard"""
    user = request.user
    
    # Stats Cards
    total_projects = Project.objects.filter(customer=user).count()
    completed_projects = Project.objects.filter(customer=user, status='completed').count()
    active_projects = Project.objects.filter(
        customer=user,
        status__in=['deposit_paid', 'in_progress', 'submitted']
    ).count()
    pending_projects = Project.objects.filter(
        customer=user,
        status__in=['negotiating', 'agreed']
    ).count()
    
    total_spent = Project.objects.filter(
        customer=user,
        status='completed'
    ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0
    
    total_reviews = Review.objects.filter(customer=user).count()
    
    # Unread counts
    conversations = Conversation.objects.filter(participants=user)
    unread_messages = Message.objects.filter(
        conversation__in=conversations,
        is_read=False
    ).exclude(sender=user).count()
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
    
    # Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)
    
    stats = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'active_projects': active_projects,
        'pending_projects': pending_projects,
        'total_spent': total_spent,
        'total_reviews': total_reviews,
        'unread_messages': unread_messages,
        'unread_notifications': unread_notifications,
        'wallet_balance': wallet.balance,
    }
    
    # Spending Chart Data (Last 30 days)
    spending_data = get_spending_chart_data(user)
    
    # Recent Projects
    recent_projects = Project.objects.filter(
        customer=user
    ).select_related('provider', 'service').order_by('-created_at')[:5]
    
    # Status Distribution
    status_distribution = {
        'negotiating': Project.objects.filter(customer=user, status='negotiating').count(),
        'agreed': Project.objects.filter(customer=user, status='agreed').count(),
        'deposit_paid': Project.objects.filter(customer=user, status='deposit_paid').count(),
        'in_progress': Project.objects.filter(customer=user, status='in_progress').count(),
        'submitted': Project.objects.filter(customer=user, status='submitted').count(),
        'completed': Project.objects.filter(customer=user, status='completed').count(),
        'disputed': Project.objects.filter(customer=user, status='disputed').count(),
        'cancelled': Project.objects.filter(customer=user, status='cancelled').count(),
    }
    
    # Recent Activities
    recent_activities = ProjectActivity.objects.filter(
        project__customer=user
    ).select_related('project', 'user').order_by('-created_at')[:10]
    
    # Favorite Providers
    favorite_providers = User.objects.filter(
        projects_as_provider__customer=user,
        projects_as_provider__status='completed'
    ).distinct().order_by('-rating')[:5]
    
    context = {
        'stats': stats,
        'spending_data': spending_data,
        'recent_projects': recent_projects,
        'status_distribution': status_distribution,
        'recent_activities': recent_activities,
        'favorite_providers': favorite_providers,
    }
    
    return context


def get_earnings_chart_data(user):
    """Get earnings data for chart"""
    end_date = timezone.now()
    dates = []
    values = []
    
    for i in range(30, -1, -1):
        date = end_date - timedelta(days=i)
        dates.append(date.strftime('%b %d'))
        
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        daily_earnings = Project.objects.filter(
            provider=user,
            status='completed',
            completed_at__gte=day_start,
            completed_at__lte=day_end
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
        
        values.append(float(daily_earnings))
    
    return {
        'dates': dates,
        'values': values,
    }


def get_spending_chart_data(user):
    """Get spending data for chart"""
    end_date = timezone.now()
    dates = []
    values = []
    
    for i in range(30, -1, -1):
        date = end_date - timedelta(days=i)
        dates.append(date.strftime('%b %d'))
        
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        daily_spending = Project.objects.filter(
            customer=user,
            status='completed',
            completed_at__gte=day_start,
            completed_at__lte=day_end
        ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0
        
        values.append(float(daily_spending))
    
    return {
        'dates': dates,
        'values': values,
    }


def get_monthly_performance(user):
    """Get monthly performance data"""
    months = []
    earnings = []
    projects = []
    
    for i in range(6, -1, -1):
        month_date = timezone.now() - timedelta(days=i*30)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)
        
        months.append(month_start.strftime('%b %Y'))
        
        monthly_earnings = Project.objects.filter(
            provider=user,
            status='completed',
            completed_at__gte=month_start,
            completed_at__lt=next_month_start
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
        
        earnings.append(float(monthly_earnings))
        
        monthly_projects = Project.objects.filter(
            provider=user,
            created_at__gte=month_start,
            created_at__lt=next_month_start
        ).count()
        
        projects.append(monthly_projects)
    
    return {
        'months': months,
        'earnings': earnings,
        'projects': projects,
    }


@login_required
@require_GET
def get_dashboard_stats(request):
    """Get dashboard statistics via AJAX"""
    user = request.user
    
    if user.is_provider():
        stats = {
            'total_projects': Project.objects.filter(provider=user).count(),
            'completed_projects': Project.objects.filter(provider=user, status='completed').count(),
            'pending_projects': Project.objects.filter(
                provider=user,
                status__in=['deposit_paid', 'in_progress', 'submitted']
            ).count(),
            'total_earnings': float(Project.objects.filter(
                provider=user,
                status='completed'
            ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0),
        }
    else:
        stats = {
            'total_projects': Project.objects.filter(customer=user).count(),
            'completed_projects': Project.objects.filter(customer=user, status='completed').count(),
            'active_projects': Project.objects.filter(
                customer=user,
                status__in=['deposit_paid', 'in_progress', 'submitted']
            ).count(),
            'total_spent': float(Project.objects.filter(
                customer=user,
                status='completed'
            ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0),
        }
    
    wallet, _ = Wallet.objects.get_or_create(user=user)
    stats['wallet_balance'] = float(wallet.balance)
    
    return JsonResponse(stats)