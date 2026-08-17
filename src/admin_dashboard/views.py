# admin_dashboard/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

from accounts.models import User, Wallet
from services.models import Service, ServiceCategory
from projects.models import Project, Dispute
from payments.models import PaymentTransaction, Payout
from reviews.models import Review
from notifications.models import Notification


@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard"""
    # ============ STATS ============
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    providers = User.objects.filter(user_type__in=['provider', 'both']).count()
    customers = User.objects.filter(user_type__in=['customer', 'both']).count()
    
    total_services = Service.objects.filter(is_active=True).count()
    pending_services = Service.objects.filter(is_active=False).count()
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status='completed').count()
    
    # Revenue
    total_revenue = PaymentTransaction.objects.filter(
        status='completed',
        payment_type='final'
    ).aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
    
    total_deposits = PaymentTransaction.objects.filter(
        status='completed',
        payment_type='deposit'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Disputes
    open_disputes = Dispute.objects.filter(status='open').count()
    total_disputes = Dispute.objects.count()
    
    # Reviews
    total_reviews = Review.objects.count()
    avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    new_users = User.objects.filter(date_joined__gte=week_ago).count()
    new_services = Service.objects.filter(created_at__gte=week_ago).count()
    new_projects = Project.objects.filter(created_at__gte=week_ago).count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'providers': providers,
        'customers': customers,
        'total_services': total_services,
        'pending_services': pending_services,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'total_revenue': total_revenue,
        'total_deposits': total_deposits,
        'open_disputes': open_disputes,
        'total_disputes': total_disputes,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'new_users': new_users,
        'new_services': new_services,
        'new_projects': new_projects,
    }
    
    # Recent users
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    
    # Recent projects
    recent_projects = Project.objects.all().select_related('customer', 'provider').order_by('-created_at')[:10]
    
    # Recent payments
    recent_payments = PaymentTransaction.objects.filter(
        status='completed'
    ).select_related('user', 'project').order_by('-created_at')[:10]
    
    # Recent disputes
    recent_disputes = Dispute.objects.all().select_related('project', 'user').order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_users': recent_users,
        'recent_projects': recent_projects,
        'recent_payments': recent_payments,
        'recent_disputes': recent_disputes,
        'title': 'Dashboard',
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def admin_users(request):
    """Manage users"""
    users = User.objects.all().order_by('-date_joined')
    
    # Filters
    user_type = request.GET.get('type')
    if user_type:
        users = users.filter(user_type=user_type)
    
    verification_status = request.GET.get('verification')
    if verification_status:
        users = users.filter(verification_status=verification_status)
    
    is_active = request.GET.get('active')
    if is_active == 'true':
        users = users.filter(is_active=True)
    elif is_active == 'false':
        users = users.filter(is_active=False)
    
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    context = {
        'users': users,
        'user_types': User.USER_TYPES,
        'verification_statuses': User.VERIFICATION_STATUS,
        'title': 'Users',
    }
    return render(request, 'admin_dashboard/users.html', context)


@staff_member_required
def admin_user_detail(request, user_id):
    """View user details"""
    user = get_object_or_404(User, id=user_id)
    
    # User stats
    if user.is_provider():
        services = Service.objects.filter(provider=user)
        total_services = services.count()
        projects_as_provider = Project.objects.filter(provider=user)
        total_projects = projects_as_provider.count()
        completed_projects = projects_as_provider.filter(status='completed').count()
        total_earnings = projects_as_provider.filter(
            status='completed'
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
        total_reviews = Review.objects.filter(provider=user).count()
    else:
        services = []
        total_services = 0
        projects_as_provider = []
        total_projects = 0
        completed_projects = 0
        total_earnings = 0
        total_reviews = 0
    
    projects_as_customer = Project.objects.filter(customer=user)
    total_customer_projects = projects_as_customer.count()
    completed_customer_projects = projects_as_customer.filter(status='completed').count()
    
    wallet, _ = Wallet.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            user.verification_status = 'verified'
            user.verified_at = timezone.now()
            user.save()
            messages.success(request, f'User {user.username} verified successfully!')
        
        elif action == 'reject':
            user.verification_status = 'rejected'
            user.save()
            messages.success(request, f'User {user.username} rejected.')
        
        elif action == 'suspend':
            user.is_active = False
            user.save()
            messages.success(request, f'User {user.username} suspended.')
        
        elif action == 'activate':
            user.is_active = True
            user.save()
            messages.success(request, f'User {user.username} activated.')
        
        elif action == 'make_admin':
            user.is_staff = True
            user.save()
            messages.success(request, f'User {user.username} is now an admin.')
        
        elif action == 'remove_admin':
            user.is_staff = False
            user.save()
            messages.success(request, f'Admin rights removed from {user.username}.')
        
        elif action == 'delete':
            user.delete()
            messages.success(request, f'User {user.username} deleted.')
            return redirect('admin_dashboard:users')
        
        return redirect('admin_dashboard:user_detail', user_id=user.id)
    
    context = {
        'user_detail': user,
        'services': services,
        'total_services': total_services,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'total_earnings': total_earnings,
        'total_reviews': total_reviews,
        'total_customer_projects': total_customer_projects,
        'completed_customer_projects': completed_customer_projects,
        'wallet': wallet,
        'title': f'User: {user.username}',
    }
    return render(request, 'admin_dashboard/user_detail.html', context)


@staff_member_required
def admin_services(request):
    """Manage services"""
    services = Service.objects.all().select_related('provider', 'category').order_by('-created_at')
    
    # Filters
    is_active = request.GET.get('active')
    if is_active == 'true':
        services = services.filter(is_active=True)
    elif is_active == 'false':
        services = services.filter(is_active=False)
    
    category = request.GET.get('category')
    if category:
        services = services.filter(category_id=category)
    
    search = request.GET.get('search')
    if search:
        services = services.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(provider__username__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(services, 20)
    page = request.GET.get('page')
    
    try:
        services = paginator.page(page)
    except PageNotAnInteger:
        services = paginator.page(1)
    except EmptyPage:
        services = paginator.page(paginator.num_pages)
    
    categories = ServiceCategory.objects.filter(is_active=True)
    
    context = {
        'services': services,
        'categories': categories,
        'title': 'Services',
    }
    return render(request, 'admin_dashboard/services.html', context)


@staff_member_required
def admin_service_detail(request, service_id):
    """View service details"""
    service = get_object_or_404(Service, id=service_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            service.is_active = True
            service.save()
            messages.success(request, f'Service "{service.title}" approved!')
        
        elif action == 'reject':
            service.is_active = False
            service.save()
            messages.success(request, f'Service "{service.title}" rejected.')
        
        elif action == 'feature':
            service.is_featured = True
            service.save()
            messages.success(request, f'Service "{service.title}" featured!')
        
        elif action == 'unfeature':
            service.is_featured = False
            service.save()
            messages.success(request, f'Service "{service.title}" unfeatured.')
        
        elif action == 'delete':
            service.delete()
            messages.success(request, f'Service "{service.title}" deleted.')
            return redirect('admin_dashboard:services')
        
        return redirect('admin_dashboard:service_detail', service_id=service.id)
    
    context = {
        'service': service,
        'title': f'Service: {service.title}',
    }
    return render(request, 'admin_dashboard/service_detail.html', context)


@staff_member_required
def admin_projects(request):
    """Manage projects"""
    projects = Project.objects.all().select_related('customer', 'provider', 'service').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        projects = projects.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(customer__username__icontains=search) |
            Q(provider__username__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(projects, 20)
    page = request.GET.get('page')
    
    try:
        projects = paginator.page(page)
    except PageNotAnInteger:
        projects = paginator.page(1)
    except EmptyPage:
        projects = paginator.page(paginator.num_pages)
    
    context = {
        'projects': projects,
        'status_choices': Project.STATUS_CHOICES,
        'title': 'Projects',
    }
    return render(request, 'admin_dashboard/projects.html', context)


@staff_member_required
def admin_project_detail(request, project_id):
    """View project details"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_completed':
            project.status = 'completed'
            project.completed_at = timezone.now()
            project.save()
            messages.success(request, f'Project "{project.title}" marked as completed!')
        
        elif action == 'cancel':
            project.status = 'cancelled'
            project.save()
            messages.success(request, f'Project "{project.title}" cancelled.')
        
        elif action == 'refund':
            # Process refund logic here
            messages.success(request, f'Refund processed for project "{project.title}".')
        
        return redirect('admin_dashboard:project_detail', project_id=project.id)
    
    context = {
        'project': project,
        'title': f'Project: {project.title}',
    }
    return render(request, 'admin_dashboard/project_detail.html', context)


@staff_member_required
def admin_payments(request):
    """Manage payments"""
    payments = PaymentTransaction.objects.all().select_related('user', 'project').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    payment_type = request.GET.get('type')
    if payment_type:
        payments = payments.filter(payment_type=payment_type)
    
    # Pagination
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    
    try:
        payments = paginator.page(page)
    except PageNotAnInteger:
        payments = paginator.page(1)
    except EmptyPage:
        payments = paginator.page(paginator.num_pages)
    
    context = {
        'payments': payments,
        'status_choices': PaymentTransaction.STATUS_CHOICES,
        'payment_types': PaymentTransaction.PAYMENT_TYPES,
        'title': 'Payments',
    }
    return render(request, 'admin_dashboard/payments.html', context)


@staff_member_required
def admin_disputes(request):
    """Manage disputes"""
    disputes = Dispute.objects.all().select_related('project', 'user').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    if status:
        disputes = disputes.filter(status=status)
    
    context = {
        'disputes': disputes,
        'status_choices': Dispute.DISPUTE_STATUS,
        'title': 'Disputes',
    }
    return render(request, 'admin_dashboard/disputes.html', context)


@staff_member_required
def admin_dispute_detail(request, dispute_id):
    """View dispute details"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        resolution = request.POST.get('resolution', '')
        
        if action == 'resolve':
            dispute.status = 'resolved'
            dispute.resolution = resolution
            dispute.resolved_by = request.user
            dispute.resolved_at = timezone.now()
            dispute.save()
            
            # Update project
            dispute.project.dispute_resolved = True
            dispute.project.status = 'in_progress'
            dispute.project.save()
            
            messages.success(request, 'Dispute resolved successfully!')
        
        elif action == 'escalate':
            dispute.status = 'escalated'
            dispute.is_escalated = True
            dispute.escalated_at = timezone.now()
            dispute.save()
            messages.success(request, 'Dispute escalated to admin review.')
        
        elif action == 'close':
            dispute.status = 'closed'
            dispute.save()
            messages.success(request, 'Dispute closed.')
        
        return redirect('admin_dashboard:dispute_detail', dispute_id=dispute.id)
    
    context = {
        'dispute': dispute,
        'title': f'Dispute: {dispute.title}',
    }
    return render(request, 'admin_dashboard/dispute_detail.html', context)


@staff_member_required
def admin_reviews(request):
    """Manage reviews"""
    reviews = Review.objects.all().select_related('provider', 'customer').order_by('-created_at')
    
    # Filters
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    is_verified = request.GET.get('verified')
    if is_verified == 'true':
        reviews = reviews.filter(is_verified=True)
    elif is_verified == 'false':
        reviews = reviews.filter(is_verified=False)
    
    is_hidden = request.GET.get('hidden')
    if is_hidden == 'true':
        reviews = reviews.filter(is_hidden=True)
    elif is_hidden == 'false':
        reviews = reviews.filter(is_hidden=False)
    
    context = {
        'reviews': reviews,
        'title': 'Reviews',
    }
    return render(request, 'admin_dashboard/reviews.html', context)


@staff_member_required
@require_POST
def admin_bulk_action(request):
    """Handle bulk actions on users"""
    action = request.POST.get('bulk_action')
    selected_ids = request.POST.getlist('selected_ids')
    
    if not selected_ids:
        messages.error(request, 'No items selected.')
        return redirect(request.META.get('HTTP_REFERER', '/admin-dashboard/'))
    
    if action == 'verify':
        User.objects.filter(id__in=selected_ids).update(verification_status='verified')
        messages.success(request, f'{len(selected_ids)} users verified.')
    
    elif action == 'suspend':
        User.objects.filter(id__in=selected_ids).update(is_active=False)
        messages.success(request, f'{len(selected_ids)} users suspended.')
    
    elif action == 'activate':
        User.objects.filter(id__in=selected_ids).update(is_active=True)
        messages.success(request, f'{len(selected_ids)} users activated.')
    
    elif action == 'delete':
        User.objects.filter(id__in=selected_ids).delete()
        messages.success(request, f'{len(selected_ids)} users deleted.')
    
    return redirect(request.META.get('HTTP_REFERER', '/admin-dashboard/'))

@staff_member_required
@require_POST
def admin_review_action(request):
    """Handle review actions (verify, hide, delete)"""
    review_id = request.POST.get('review_id')
    action = request.POST.get('action')
    
    review = get_object_or_404(Review, id=review_id)
    
    if action == 'verify':
        review.is_verified = True
        review.save()
        messages.success(request, 'Review verified successfully!')
    
    elif action == 'hide':
        review.is_hidden = True
        review.is_public = False
        review.save()
        messages.success(request, 'Review hidden successfully!')
    
    elif action == 'show':
        review.is_hidden = False
        review.is_public = True
        review.save()
        messages.success(request, 'Review shown successfully!')
    
    elif action == 'delete':
        review.delete()
        messages.success(request, 'Review deleted successfully!')
    
    return redirect('admin_dashboard:reviews')