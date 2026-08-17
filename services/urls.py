from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Service listing and search
    path('', views.service_list, name='list'),
    path('search/', views.service_search, name='search'),
    
    # Service CRUD operations
    path('create/', views.service_create, name='create'),
    path('<int:service_id>/', views.service_detail, name='detail'),
    path('<int:service_id>/edit/', views.service_edit, name='edit'),
    path('<int:service_id>/delete/', views.service_delete, name='delete'),
    
    # Service portfolio (gallery)
    path('<int:service_id>/portfolio/add/', views.add_portfolio, name='add_portfolio'),
    path('portfolio/<int:portfolio_id>/delete/', views.delete_portfolio, name='delete_portfolio'),
    
    # Categories
    path('categories/', views.category_list, name='categories'),
    path('category/<slug:category_slug>/', views.category_detail, name='category_detail'),
    
    # Provider services
    path('my-services/', views.my_services, name='my_services'),
    path('provider/<int:provider_id>/', views.provider_services, name='provider_services'),
]