# reviews/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Review(models.Model):
    """Reviews for providers"""
    
    RATING_CHOICES = (
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    )
    
    # Relationships
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews_received'
    )
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews_given'
    )
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviews'
    )
    
    # Review content
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    # Review categories
    categories = models.JSONField(default=list, blank=True, help_text="Categories like: quality, communication, delivery, etc.")
    
    # Status
    is_public = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Verified purchase
    is_hidden = models.BooleanField(default=False)  # Hidden by admin
    is_reported = models.BooleanField(default=False)
    
    # Helpful votes
    helpful_count = models.IntegerField(default=0)
    unhelpful_count = models.IntegerField(default=0)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, null=True)
    hidden_reason = models.CharField(max_length=255, blank=True, null=True)
    
    # Response from provider
    response = models.TextField(blank=True, null=True)
    response_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['customer', 'project']  # One review per project per customer
    
    def __str__(self):
        return f"Review by {self.customer.username} for {self.provider.username} - {self.rating} stars"
    
    def get_rating_display(self):
        return dict(self.RATING_CHOICES).get(self.rating, 'Not rated')
    
    def get_star_display(self):
        return '⭐' * self.rating
    
    def get_time_ago(self):
        """Get human-readable time ago"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 7:
            return f"{diff.days // 7} weeks ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"
    
    def add_helpful(self, user):
        """Add a helpful vote"""
        from .models import ReviewHelpful
        obj, created = ReviewHelpful.objects.get_or_create(
            review=self,
            user=user,
            defaults={'is_helpful': True}
        )
        if created:
            self.helpful_count += 1
            self.save()
            return True
        return False
    
    def add_unhelpful(self, user):
        """Add an unhelpful vote"""
        from .models import ReviewHelpful
        obj, created = ReviewHelpful.objects.get_or_create(
            review=self,
            user=user,
            defaults={'is_helpful': False}
        )
        if created:
            self.unhelpful_count += 1
            self.save()
            return True
        return False
    
    def add_response(self, user, response):
        """Add a response to the review"""
        if user == self.provider:
            self.response = response
            self.response_at = timezone.now()
            self.save()
            return True
        return False


class ReviewHelpful(models.Model):
    """Track helpful votes on reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {'Helpful' if self.is_helpful else 'Unhelpful'} - {self.review.id}"


class ReviewReport(models.Model):
    """Reports for inappropriate reviews"""
    
    REPORT_REASONS = (
        ('spam', 'Spam'),
        ('offensive', 'Offensive Content'),
        ('fake', 'Fake Review'),
        ('irrelevant', 'Irrelevant'),
        ('conflict', 'Conflict of Interest'),
        ('other', 'Other'),
    )
    
    REPORT_STATUS = (
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('actioned', 'Action Taken'),
        ('dismissed', 'Dismissed'),
    )
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    
    # Admin
    admin_notes = models.TextField(blank=True, null=True)
    action_taken = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report on Review {self.review.id} by {self.user.username}"


class ReviewCategory(models.Model):
    """Categories for reviews (e.g., Quality, Communication, etc.)"""
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='fas fa-tag')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Review Categories'
    
    def __str__(self):
        return self.name