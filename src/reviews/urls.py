from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Review list
    path('', views.review_list, name='list'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    
    # Create review
    path('create/<int:provider_id>/', views.create_review, name='create'),
    path('create/<int:provider_id>/<int:project_id>/', views.create_review, name='create_with_project'),
    
    # Review detail
    path('<int:review_id>/', views.review_detail, name='detail'),
    
    # Edit/Delete review
    path('<int:review_id>/edit/', views.edit_review, name='edit'),
    path('<int:review_id>/delete/', views.delete_review, name='delete'),
    
    # Provider reviews
    path('provider/<int:provider_id>/', views.provider_reviews, name='provider_reviews'),
    
    # Review statistics
    path('statistics/', views.review_statistics, name='statistics'),
    path('statistics/<int:provider_id>/', views.provider_statistics, name='provider_statistics'),
    
    # Helpful votes
    path('<int:review_id>/helpful/', views.mark_helpful, name='mark_helpful'),
    path('<int:review_id>/unhelpful/', views.mark_unhelpful, name='mark_unhelpful'),
    
    # Report review
    path('<int:review_id>/report/', views.report_review, name='report'),
    
    # Admin actions (for staff)
    path('admin/verify/<int:review_id>/', views.verify_review, name='verify'),
    path('admin/unverify/<int:review_id>/', views.unverify_review, name='unverify'),
    path('admin/hide/<int:review_id>/', views.hide_review, name='hide'),
    path('admin/show/<int:review_id>/', views.show_review, name='show'),
    
    # Search reviews
    path('search/', views.search_reviews, name='search'),
]