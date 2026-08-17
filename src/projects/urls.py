from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Project listing
    path('', views.project_list, name='list'),
    path('my-projects/', views.my_projects, name='my_projects'),
    
    # Project CRUD
    path('create/<int:service_id>/', views.project_create, name='create'),
    path('<int:project_id>/', views.project_detail, name='detail'),
    path('<int:project_id>/edit/', views.project_edit, name='edit'),
    path('<int:project_id>/delete/', views.project_delete, name='delete'),
    
    # Project workflow
    path('<int:project_id>/accept/', views.accept_project, name='accept'),
    path('<int:project_id>/start/', views.start_project, name='start'),
    path('<int:project_id>/submit/', views.submit_work, name='submit_work'),
    path('<int:project_id>/complete/', views.complete_project, name='complete'),
    path('<int:project_id>/cancel/', views.cancel_project, name='cancel'),
    
    # Payments
    path('<int:project_id>/pay-deposit/', views.pay_deposit, name='pay_deposit'),
    path('<int:project_id>/pay-final/', views.pay_final, name='pay_final'),
    
    # Disputes
    path('<int:project_id>/dispute/', views.create_dispute, name='create_dispute'),
    path('dispute/<int:dispute_id>/', views.dispute_detail, name='dispute_detail'),
    
    # Project updates and messages
    path('<int:project_id>/add-update/', views.add_project_update, name='add_update'),
    path('<int:project_id>/messages/', views.project_messages, name='messages'),
]