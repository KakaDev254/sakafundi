# reviews/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.urls import reverse

from .models import Review, ReviewHelpful, ReviewReport, ReviewCategory
from .forms import ReviewForm, ReviewResponseForm, ReviewReportForm
from accounts.models import User
from projects.models import Project
from notifications.models import Notification


@login_required
def review_list(request):
    """List all reviews for the user (as provider)"""
    user = request.user
    
    # Get reviews where user is the provider
    reviews = Review.objects.filter(
        provider=user,
        is_public=True,
        is_hidden=False
    ).select_related('customer', 'project').order_by('-created_at')
    
    # Filter by rating
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    # Filter by verified
    verified = request.GET.get('verified')
    if verified == 'true':
        reviews = reviews.filter(is_verified=True)
    elif verified == 'false':
        reviews = reviews.filter(is_verified=False)
    
    # Search
    query = request.GET.get('q')
    if query:
        reviews = reviews.filter(
            Q(title__icontains=query) |
            Q(comment__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(reviews, 10)
    page = request.GET.get('page')
    
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)
    
    # Statistics
    stats = {
        'total': Review.objects.filter(provider=user, is_public=True, is_hidden=False).count(),
        'average': Review.objects.filter(provider=user, is_public=True, is_hidden=False).aggregate(Avg('rating'))['rating__avg'] or 0,
        '5_star': Review.objects.filter(provider=user, rating=5, is_public=True, is_hidden=False).count(),
        '4_star': Review.objects.filter(provider=user, rating=4, is_public=True, is_hidden=False).count(),
        '3_star': Review.objects.filter(provider=user, rating=3, is_public=True, is_hidden=False).count(),
        '2_star': Review.objects.filter(provider=user, rating=2, is_public=True, is_hidden=False).count(),
        '1_star': Review.objects.filter(provider=user, rating=1, is_public=True, is_hidden=False).count(),
        'verified': Review.objects.filter(provider=user, is_verified=True, is_public=True, is_hidden=False).count(),
    }
    
    context = {
        'reviews': reviews,
        'stats': stats,
        'rating': rating,
        'verified': verified,
        'query': query,
    }
    return render(request, 'reviews/list.html', context)


@login_required
def my_reviews(request):
    """List reviews written by the user (as customer)"""
    reviews = Review.objects.filter(
        customer=request.user
    ).select_related('provider', 'project').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reviews, 10)
    page = request.GET.get('page')
    
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)
    
    context = {
        'reviews': reviews,
        'is_my_reviews': True,
    }
    return render(request, 'reviews/my_reviews.html', context)


@login_required
def create_review(request, provider_id, project_id=None):
    """Create a review for a provider"""
    provider = get_object_or_404(User, id=provider_id, is_active=True)
    
    # Check if user is trying to review themselves
    if request.user == provider:
        messages.error(request, 'You cannot review yourself.')
        return redirect('reviews:list')
    
    # Check if review already exists
    existing_review = None
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        existing_review = Review.objects.filter(
            customer=request.user,
            project=project
        ).first()
        
        # Check if user is part of the project
        if request.user not in [project.customer, project.provider]:
            messages.error(request, 'You are not part of this project.')
            return redirect('services:list')
        
        # Check if project is completed
        if project.status != 'completed':
            messages.error(request, 'You can only review completed projects.')
            return redirect('projects:detail', project_id=project.id)
    else:
        # Check if user has completed projects with this provider
        completed_projects = Project.objects.filter(
            customer=request.user,
            provider=provider,
            status='completed'
        ).exists()
        
        if not completed_projects:
            messages.error(request, 'You can only review providers you have worked with.')
            return redirect('services:list')
    
    if existing_review:
        messages.warning(request, 'You have already reviewed this project.')
        return redirect('reviews:detail', review_id=existing_review.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.customer = request.user
            review.provider = provider
            
            if project_id:
                review.project = project
            
            review.save()
            
            # Update provider rating
            provider.update_rating()
            
            # Create notification for provider
            Notification.objects.create(
                user=provider,
                type='review',
                title='New Review',
                message=f'{request.user.get_full_name()} left you a {review.rating}-star review',
                link=f'/reviews/{review.id}/'
            )
            
            messages.success(request, 'Review submitted successfully!')
            return redirect('reviews:detail', review_id=review.id)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'provider': provider,
        'project': project if project_id else None,
    }
    return render(request, 'reviews/create.html', context)


@login_required
def review_detail(request, review_id):
    """View review details"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if user is authorized
    if request.user not in [review.customer, review.provider] and not request.user.is_staff:
        if review.is_hidden or not review.is_public:
            messages.error(request, 'This review is not available.')
            return redirect('reviews:list')
    
    # Check if user can respond
    can_respond = request.user == review.provider and not review.response
    
    # Check if user can edit
    can_edit = request.user == review.customer and timezone.now() - review.created_at < timezone.timedelta(days=7)
    
    # Check if user already voted
    has_voted = ReviewHelpful.objects.filter(
        review=review,
        user=request.user
    ).exists() if request.user.is_authenticated else False
    
    # Get helpful votes
    helpful_votes = review.helpful_votes.filter(is_helpful=True).count()
    unhelpful_votes = review.helpful_votes.filter(is_helpful=False).count()
    
    # Handle response form
    if request.method == 'POST' and can_respond:
        form = ReviewResponseForm(request.POST)
        if form.is_valid():
            review.add_response(request.user, form.cleaned_data['response'])
            messages.success(request, 'Response added successfully!')
            return redirect('reviews:detail', review_id=review.id)
    else:
        form = ReviewResponseForm() if can_respond else None
    
    context = {
        'review': review,
        'can_respond': can_respond,
        'can_edit': can_edit,
        'has_voted': has_voted,
        'helpful_votes': helpful_votes,
        'unhelpful_votes': unhelpful_votes,
        'form': form,
        'is_owner': request.user == review.customer,
    }
    return render(request, 'reviews/detail.html', context)


@login_required
def edit_review(request, review_id):
    """Edit a review"""
    review = get_object_or_404(Review, id=review_id, customer=request.user)
    
    # Check if review can be edited (within 7 days)
    if timezone.now() - review.created_at > timezone.timedelta(days=7):
        messages.error(request, 'Reviews can only be edited within 7 days of posting.')
        return redirect('reviews:detail', review_id=review.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save()
            messages.success(request, 'Review updated successfully!')
            return redirect('reviews:detail', review_id=review.id)
    else:
        form = ReviewForm(instance=review)
    
    context = {
        'form': form,
        'review': review,
    }
    return render(request, 'reviews/edit.html', context)


@login_required
@require_POST
def delete_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(Review, id=review_id, customer=request.user)
    
    # Check if review can be deleted (within 7 days)
    if timezone.now() - review.created_at > timezone.timedelta(days=7):
        messages.error(request, 'Reviews can only be deleted within 7 days of posting.')
        return redirect('reviews:detail', review_id=review.id)
    
    review.delete()
    
    # Update provider rating
    review.provider.update_rating()
    
    messages.success(request, 'Review deleted successfully!')
    return redirect('reviews:my_reviews')


@login_required
@require_POST
def mark_helpful(request, review_id):
    """Mark a review as helpful"""
    review = get_object_or_404(Review, id=review_id)
    
    if request.user == review.customer:
        return JsonResponse({'error': 'You cannot vote on your own review'}, status=400)
    
    result = review.add_helpful(request.user)
    
    return JsonResponse({
        'success': result,
        'helpful_count': review.helpful_count,
        'unhelpful_count': review.unhelpful_count
    })


@login_required
@require_POST
def mark_unhelpful(request, review_id):
    """Mark a review as unhelpful"""
    review = get_object_or_404(Review, id=review_id)
    
    if request.user == review.customer:
        return JsonResponse({'error': 'You cannot vote on your own review'}, status=400)
    
    result = review.add_unhelpful(request.user)
    
    return JsonResponse({
        'success': result,
        'helpful_count': review.helpful_count,
        'unhelpful_count': review.unhelpful_count
    })


@login_required
def provider_reviews(request, provider_id):
    """View all reviews for a provider"""
    provider = get_object_or_404(User, id=provider_id, is_active=True)
    
    reviews = Review.objects.filter(
        provider=provider,
        is_public=True,
        is_hidden=False
    ).select_related('customer', 'project').order_by('-created_at')
    
    # Filter by rating
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    # Pagination
    paginator = Paginator(reviews, 10)
    page = request.GET.get('page')
    
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)
    
    # Statistics
    stats = {
        'total': Review.objects.filter(provider=provider, is_public=True, is_hidden=False).count(),
        'average': Review.objects.filter(provider=provider, is_public=True, is_hidden=False).aggregate(Avg('rating'))['rating__avg'] or 0,
        'rating_distribution': {
            '5': Review.objects.filter(provider=provider, rating=5, is_public=True, is_hidden=False).count(),
            '4': Review.objects.filter(provider=provider, rating=4, is_public=True, is_hidden=False).count(),
            '3': Review.objects.filter(provider=provider, rating=3, is_public=True, is_hidden=False).count(),
            '2': Review.objects.filter(provider=provider, rating=2, is_public=True, is_hidden=False).count(),
            '1': Review.objects.filter(provider=provider, rating=1, is_public=True, is_hidden=False).count(),
        }
    }
    
    context = {
        'provider': provider,
        'reviews': reviews,
        'stats': stats,
        'rating': rating,
    }
    return render(request, 'reviews/provider_reviews.html', context)


@login_required
def review_statistics(request):
    """View review statistics for the user"""
    user = request.user
    
    # Statistics for reviews received
    received = Review.objects.filter(provider=user, is_public=True, is_hidden=False)
    received_stats = {
        'total': received.count(),
        'average': received.aggregate(Avg('rating'))['rating__avg'] or 0,
        'distribution': {
            '5': received.filter(rating=5).count(),
            '4': received.filter(rating=4).count(),
            '3': received.filter(rating=3).count(),
            '2': received.filter(rating=2).count(),
            '1': received.filter(rating=1).count(),
        }
    }
    
    # Statistics for reviews given
    given = Review.objects.filter(customer=user)
    given_stats = {
        'total': given.count(),
        'average': given.aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    context = {
        'received_stats': received_stats,
        'given_stats': given_stats,
        'recent_reviews': received.order_by('-created_at')[:5],
    }
    return render(request, 'reviews/statistics.html', context)


@login_required
def provider_statistics(request, provider_id):
    """View statistics for a specific provider"""
    provider = get_object_or_404(User, id=provider_id, is_active=True)
    
    reviews = Review.objects.filter(provider=provider, is_public=True, is_hidden=False)
    
    stats = {
        'total': reviews.count(),
        'average': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
        'distribution': {
            '5': reviews.filter(rating=5).count(),
            '4': reviews.filter(rating=4).count(),
            '3': reviews.filter(rating=3).count(),
            '2': reviews.filter(rating=2).count(),
            '1': reviews.filter(rating=1).count(),
        }
    }
    
    return JsonResponse(stats)


@login_required
def report_review(request, review_id):
    """Report a review"""
    review = get_object_or_404(Review, id=review_id)
    
    if request.user == review.customer:
        messages.error(request, 'You cannot report your own review.')
        return redirect('reviews:detail', review_id=review.id)
    
    # Check if already reported
    existing_report = ReviewReport.objects.filter(
        review=review,
        user=request.user,
        status='pending'
    ).exists()
    
    if existing_report:
        messages.warning(request, 'You have already reported this review.')
        return redirect('reviews:detail', review_id=review.id)
    
    if request.method == 'POST':
        form = ReviewReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.review = review
            report.user = request.user
            report.save()
            
            review.is_reported = True
            review.save()
            
            messages.success(request, 'Review reported successfully. Admin will review it.')
            return redirect('reviews:detail', review_id=review.id)
    else:
        form = ReviewReportForm()
    
    context = {
        'form': form,
        'review': review,
    }
    return render(request, 'reviews/report.html', context)


@login_required
def search_reviews(request):
    """Search for reviews"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    reviews = Review.objects.filter(
        Q(title__icontains=query) |
        Q(comment__icontains=query),
        is_public=True,
        is_hidden=False
    ).select_related('provider', 'customer')[:20]
    
    results = []
    for review in reviews:
        results.append({
            'id': review.id,
            'title': review.title,
            'rating': review.rating,
            'provider': review.provider.get_full_name(),
            'customer': review.customer.get_full_name(),
            'created_at': review.created_at.strftime('%Y-%m-%d'),
        })
    
    return JsonResponse({'results': results})


# Admin Views
@login_required
def verify_review(request, review_id):
    """Verify a review (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    review = get_object_or_404(Review, id=review_id)
    review.is_verified = True
    review.save()
    
    return JsonResponse({'success': True})


@login_required
def unverify_review(request, review_id):
    """Unverify a review (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    review = get_object_or_404(Review, id=review_id)
    review.is_verified = False
    review.save()
    
    return JsonResponse({'success': True})


@login_required
def hide_review(request, review_id):
    """Hide a review (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    review = get_object_or_404(Review, id=review_id)
    review.is_hidden = True
    review.is_public = False
    review.hidden_reason = request.POST.get('reason', 'Hidden by admin')
    review.save()
    
    return JsonResponse({'success': True})


@login_required
def show_review(request, review_id):
    """Show a review (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    review = get_object_or_404(Review, id=review_id)
    review.is_hidden = False
    review.is_public = True
    review.hidden_reason = None
    review.save()
    
    return JsonResponse({'success': True})