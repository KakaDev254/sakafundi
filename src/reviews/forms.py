# reviews/forms.py
from django import forms
from .models import Review, ReviewReport

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'categories']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Summarize your experience'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your experience with this provider...'
            }),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'rating': 'Your Rating',
            'title': 'Review Title',
            'comment': 'Your Review',
            'categories': 'Categories',
        }
        help_texts = {
            'rating': 'Select a rating from 1 to 5 stars',
            'title': 'A brief title for your review',
            'comment': 'Describe your experience in detail',
        }


class ReviewResponseForm(forms.Form):
    """Form for provider to respond to a review"""
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Thank you for your review. Here is my response...'
        }),
        label='Your Response',
        max_length=2000
    )


class ReviewReportForm(forms.ModelForm):
    class Meta:
        model = ReviewReport
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please provide details about why you are reporting this review...'
            }),
        }
        labels = {
            'reason': 'Reason for Reporting',
            'description': 'Additional Details',
        }


class ReviewFilterForm(forms.Form):
    """Form for filtering reviews"""
    rating = forms.ChoiceField(
        choices=[('', 'All Ratings')] + [(i, f'{i} Stars') for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    verified = forms.ChoiceField(
        choices=[
            ('', 'All Reviews'),
            ('true', 'Verified Only'),
            ('false', 'Unverified Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-rating', 'Highest Rated'),
            ('rating', 'Lowest Rated'),
            ('-helpful_count', 'Most Helpful'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )