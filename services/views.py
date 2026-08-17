# services/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Service, ServiceCategory, ServicePortfolio
from .forms import ServiceForm, ServicePortfolioForm
from accounts.models import User

def service_list(request):
    """List all active services with filtering and pagination"""
    services = Service.objects.filter(is_active=True).select_related('provider', 'category')
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        services = services.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(provider__first_name__icontains=query) |
            Q(provider__last_name__icontains=query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        services = services.filter(category_id=category_id)
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        services = services.filter(price_min__gte=min_price)
    if max_price:
        services = services.filter(price_max__lte=max_price)
    
    # Rating filter
    rating = request.GET.get('rating')
    if rating:
        services = services.filter(rating__gte=rating)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['created_at', '-created_at', 'price_min', '-price_min', 'rating', '-rating', 'title']:
        services = services.order_by(sort_by)
    else:
        services = services.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(services, 12)  # 12 services per page
    page = request.GET.get('page')
    
    try:
        services = paginator.page(page)
    except PageNotAnInteger:
        services = paginator.page(1)
    except EmptyPage:
        services = paginator.page(paginator.num_pages)
    
    # Get all categories for filter
    categories = ServiceCategory.objects.filter(is_active=True)
    
    context = {
        'services': services,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'rating': rating,
        'sort_by': sort_by,
        'total_count': paginator.count,
    }
    return render(request, 'services/list.html', context)

def service_search(request):
    """AJAX search endpoint for services"""
    query = request.GET.get('q', '')
    if query:
        services = Service.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        )[:10]
        
        results = []
        for service in services:
            results.append({
                'id': service.id,
                'title': service.title,
                'price_min': str(service.price_min),
                'price_max': str(service.price_max),
                'provider': service.provider.get_full_name(),
                'category': service.category.name,
            })
        
        return JsonResponse({'results': results})
    
    return JsonResponse({'results': []})

def service_detail(request, service_id):
    """View service details"""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    # Increment view count
    service.views += 1
    service.save()
    
    # Get portfolio images
    portfolio = service.portfolio.all()
    
    # Get similar services
    similar_services = Service.objects.filter(
        category=service.category,
        is_active=True
    ).exclude(id=service.id)[:4]
    
    # Check if user can review (has completed projects with this provider)
    can_review = False
    if request.user.is_authenticated:
        from projects.models import Project
        can_review = Project.objects.filter(
            customer=request.user,
            provider=service.provider,
            status='completed'
        ).exists()
    
    context = {
        'service': service,
        'portfolio': portfolio,
        'similar_services': similar_services,
        'can_review': can_review,
        'provider': service.provider,
    }
    return render(request, 'services/detail.html', context)

@login_required
def service_create(request):
    """Create a new service"""
    if not request.user.is_provider():
        messages.error(request, 'You need to be a provider to create services.')
        return redirect('accounts:become_provider')
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save(commit=False)
            service.provider = request.user
            service.save()
            
            # Handle portfolio images
            images = request.FILES.getlist('portfolio_images')
            for image in images:
                ServicePortfolio.objects.create(
                    service=service,
                    image=image,
                    is_cover=not ServicePortfolio.objects.filter(service=service).exists()
                )
            
            messages.success(request, 'Your service has been created successfully!')
            return redirect('services:detail', service_id=service.id)
    else:
        form = ServiceForm()
    
    categories = ServiceCategory.objects.filter(is_active=True)
    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'services/create.html', context)

@login_required
def service_edit(request, service_id):
    """Edit an existing service"""
    service = get_object_or_404(Service, id=service_id, provider=request.user)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            service = form.save()
            messages.success(request, 'Your service has been updated successfully!')
            return redirect('services:detail', service_id=service.id)
    else:
        form = ServiceForm(instance=service)
    
    context = {
        'form': form,
        'service': service,
    }
    return render(request, 'services/edit.html', context)

@login_required
def service_delete(request, service_id):
    """Delete a service"""
    service = get_object_or_404(Service, id=service_id, provider=request.user)
    
    if request.method == 'POST':
        service.is_active = False
        service.save()
        messages.success(request, 'Your service has been deleted.')
        return redirect('services:my_services')
    
    return render(request, 'services/delete_confirm.html', {'service': service})

@login_required
def my_services(request):
    """List services created by the logged-in provider"""
    services = Service.objects.filter(provider=request.user).order_by('-created_at')
    
    context = {
        'services': services,
        'total_services': services.count(),
        'active_services': services.filter(is_active=True).count(),
    }
    return render(request, 'services/my_services.html', context)

def provider_services(request, provider_id):
    """List all services by a specific provider"""
    provider = get_object_or_404(User, id=provider_id, is_active=True)
    services = Service.objects.filter(provider=provider, is_active=True)
    
    context = {
        'provider': provider,
        'services': services,
        'total_services': services.count(),
    }
    return render(request, 'services/provider_services.html', context)

@login_required
def add_portfolio(request, service_id):
    """Add portfolio image to a service"""
    service = get_object_or_404(Service, id=service_id, provider=request.user)
    
    if request.method == 'POST':
        form = ServicePortfolioForm(request.POST, request.FILES)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.service = service
            
            # Set as cover if no cover exists
            if not ServicePortfolio.objects.filter(service=service, is_cover=True).exists():
                portfolio.is_cover = True
            
            portfolio.save()
            messages.success(request, 'Portfolio image added successfully!')
            return redirect('services:detail', service_id=service.id)
    else:
        form = ServicePortfolioForm()
    
    return render(request, 'services/add_portfolio.html', {'form': form, 'service': service})

@login_required
@require_POST
def delete_portfolio(request, portfolio_id):
    """Delete a portfolio image"""
    portfolio = get_object_or_404(ServicePortfolio, id=portfolio_id, service__provider=request.user)
    
    # If deleting cover, set another image as cover
    if portfolio.is_cover:
        other_portfolio = ServicePortfolio.objects.filter(service=portfolio.service).exclude(id=portfolio.id).first()
        if other_portfolio:
            other_portfolio.is_cover = True
            other_portfolio.save()
    
    portfolio.delete()
    messages.success(request, 'Portfolio image removed.')
    return redirect('services:detail', service_id=portfolio.service.id)

def category_list(request):
    """List all service categories"""
    categories = ServiceCategory.objects.filter(is_active=True).annotate(
        service_count=Count('services', filter=Q(services__is_active=True))
    )
    
    context = {
        'categories': categories,
    }
    return render(request, 'services/categories.html', context)

def category_detail(request, category_slug):
    """View services in a specific category"""
    category = get_object_or_404(ServiceCategory, slug=category_slug, is_active=True)
    services = Service.objects.filter(category=category, is_active=True)
    
    # Pagination
    paginator = Paginator(services, 12)
    page = request.GET.get('page')
    
    try:
        services = paginator.page(page)
    except PageNotAnInteger:
        services = paginator.page(1)
    except EmptyPage:
        services = paginator.page(paginator.num_pages)
    
    context = {
        'category': category,
        'services': services,
        'total_count': paginator.count,
    }
    return render(request, 'services/category_detail.html', context)