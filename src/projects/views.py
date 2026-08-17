# projects/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import json

from .models import (
    Project, ProjectUpdate, Dispute, ProjectMilestone, 
    ProjectDocument, ProjectActivity, ProjectInvitation
)
from .forms import (
    ProjectForm, ProjectUpdateForm, DisputeForm, 
    ProjectMilestoneForm, ProjectDocumentForm, 
    ProjectInvitationForm, ProjectFilterForm
)
from services.models import Service
from accounts.models import User
from notifications.models import Notification


@login_required
def project_list(request):
    """List all projects with filters"""
    user = request.user
    
    # Base queryset - projects where user is either customer or provider
    projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user)
    ).select_related('customer', 'provider', 'service')
    
    # Filter form
    filter_form = ProjectFilterForm(request.GET)
    
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        role = filter_form.cleaned_data.get('role')
        search = filter_form.cleaned_data.get('search')
        sort_by = filter_form.cleaned_data.get('sort_by', '-created_at')
        
        if status:
            projects = projects.filter(status=status)
        
        if role == 'customer':
            projects = projects.filter(customer=user)
        elif role == 'provider':
            projects = projects.filter(provider=user)
        
        if search:
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(provider__first_name__icontains=search) |
                Q(provider__last_name__icontains=search)
            )
        
        if sort_by:
            projects = projects.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(projects, 10)
    page = request.GET.get('page')
    
    try:
        projects = paginator.page(page)
    except PageNotAnInteger:
        projects = paginator.page(1)
    except EmptyPage:
        projects = paginator.page(paginator.num_pages)
    
    # Status counts
    status_counts = {
        'all': Project.objects.filter(Q(customer=user) | Q(provider=user)).count(),
        'draft': Project.objects.filter(Q(customer=user) | Q(provider=user), status='draft').count(),
        'negotiating': Project.objects.filter(Q(customer=user) | Q(provider=user), status='negotiating').count(),
        'agreed': Project.objects.filter(Q(customer=user) | Q(provider=user), status='agreed').count(),
        'deposit_paid': Project.objects.filter(Q(customer=user) | Q(provider=user), status='deposit_paid').count(),
        'in_progress': Project.objects.filter(Q(customer=user) | Q(provider=user), status='in_progress').count(),
        'submitted': Project.objects.filter(Q(customer=user) | Q(provider=user), status='submitted').count(),
        'completed': Project.objects.filter(Q(customer=user) | Q(provider=user), status='completed').count(),
        'disputed': Project.objects.filter(Q(customer=user) | Q(provider=user), status='disputed').count(),
        'cancelled': Project.objects.filter(Q(customer=user) | Q(provider=user), status='cancelled').count(),
    }
    
    context = {
        'projects': projects,
        'status_counts': status_counts,
        'filter_form': filter_form,
        'is_paginated': projects.has_other_pages(),
    }
    return render(request, 'projects/list.html', context)


@login_required
def my_projects(request):
    """Redirect to project list with role filter"""
    return redirect('projects:list')


@login_required
def project_create(request, service_id):
    """Create a new project from a service"""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    if request.user == service.provider:
        messages.error(request, 'You cannot hire yourself!')
        return redirect('services:detail', service_id=service.id)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.customer = request.user
            project.provider = service.provider
            project.service = service
            
            # Calculate pricing
            project.agreed_price = form.cleaned_data['agreed_price']
            project.deposit_percentage = service.deposit_percentage
            project.deposit_amount = project.calculate_deposit()
            project.final_amount = project.agreed_price - project.deposit_amount
            project.platform_fee = project.calculate_platform_fee()
            project.provider_payout = project.calculate_provider_payout()
            
            project.status = 'negotiating'
            project.save()
            
            # Create project activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='created',
                description=f'Project created by {request.user.get_full_name()}'
            )
            
            # Create notification for provider
            Notification.objects.create(
                user=service.provider,
                type='project',
                title='New Project Request',
                message=f'{request.user.get_full_name()} wants to hire you for "{project.title}"',
                link=f'/projects/{project.id}/'
            )
            
            messages.success(request, 'Project created successfully! Waiting for provider to accept.')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectForm(initial={
            'agreed_price': service.price_min,
        })
    
    context = {
        'form': form,
        'service': service,
    }
    return render(request, 'projects/create.html', context)


@login_required
def project_detail(request, project_id):
    """View project details"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user is authorized
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to view this project.')
        return redirect('projects:list')
    
    # Get project updates
    updates = project.updates.all().order_by('-created_at')[:10]
    
    # Get milestones
    milestones = project.milestones.all().order_by('order', 'due_date')
    
    # Get documents
    documents = project.documents.all().order_by('-created_at')
    
    # Get activities
    activities = project.activities.all().order_by('-created_at')[:20]
    
    # Get chat conversation
    try:
        from chat.models import Conversation
        conversation = Conversation.objects.get(project_id=project.id)
    except Conversation.DoesNotExist:
        conversation = None
    
    # Check if user can review
    can_review = False
    if project.status == 'completed' and request.user == project.customer:
        from reviews.models import Review
        can_review = not Review.objects.filter(project_id=project.id).exists()
    
    # Check permissions
    is_customer = request.user == project.customer
    is_provider = request.user == project.provider
    
    context = {
        'project': project,
        'updates': updates,
        'milestones': milestones,
        'documents': documents,
        'activities': activities,
        'conversation': conversation,
        'can_review': can_review,
        'is_customer': is_customer,
        'is_provider': is_provider,
        'can_edit': project.can_edit(request.user),
        'can_accept': project.can_accept(request.user),
        'can_start': project.can_start(request.user),
        'can_submit': project.can_submit(request.user),
        'can_complete': project.can_complete(request.user),
        'can_pay_deposit': project.can_pay_deposit(request.user),
        'can_pay_final': project.can_pay_final(request.user),
        'can_dispute': project.can_dispute(request.user),
    }
    return render(request, 'projects/detail.html', context)


@login_required
def project_edit(request, project_id):
    """Edit project details"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_edit(request.user):
        messages.error(request, 'You cannot edit this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='updated',
                description=f'Project updated by {request.user.get_full_name()}'
            )
            
            messages.success(request, 'Project updated successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/edit.html', context)


@login_required
def project_delete(request, project_id):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_edit(request.user):
        messages.error(request, 'You cannot delete this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully.')
        return redirect('projects:list')
    
    return render(request, 'projects/delete_confirm.html', {'project': project})


@login_required
def accept_project(request, project_id):
    """Provider accepts the project"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_accept(request.user):
        messages.error(request, 'You cannot accept this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        project.status = 'agreed'
        project.agreed_at = timezone.now()
        project.save()
        
        ProjectActivity.objects.create(
            project=project,
            user=request.user,
            activity_type='status_change',
            description=f'Project accepted by {request.user.get_full_name()}'
        )
        
        Notification.objects.create(
            user=project.customer,
            type='project',
            title='Project Accepted',
            message=f'{request.user.get_full_name()} has accepted your project "{project.title}"',
            link=f'/projects/{project.id}/'
        )
        
        messages.success(request, 'Project accepted! Customer can now make the deposit.')
        return redirect('projects:detail', project_id=project.id)
    
    return render(request, 'projects/accept.html', {'project': project})


@login_required
def start_project(request, project_id):
    """Provider starts working on the project"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_start(request.user):
        messages.error(request, 'You cannot start this project. Make sure deposit is paid.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        project.status = 'in_progress'
        project.started_at = timezone.now()
        project.save()
        
        ProjectActivity.objects.create(
            project=project,
            user=request.user,
            activity_type='status_change',
            description=f'Work started by {request.user.get_full_name()}'
        )
        
        Notification.objects.create(
            user=project.customer,
            type='project',
            title='Work Started',
            message=f'{request.user.get_full_name()} has started working on your project "{project.title}"',
            link=f'/projects/{project.id}/'
        )
        
        messages.success(request, 'Project started! Good luck with the work.')
        return redirect('projects:detail', project_id=project.id)
    
    return render(request, 'projects/start.html', {'project': project})


@login_required
def submit_work(request, project_id):
    """Provider submits completed work"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_submit(request.user):
        messages.error(request, 'You cannot submit work for this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        form = ProjectUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.project = project
            update.user = request.user
            update.type = 'submission'
            update.save()
            
            project.status = 'submitted'
            project.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='status_change',
                description=f'Work submitted by {request.user.get_full_name()}'
            )
            
            Notification.objects.create(
                user=project.customer,
                type='project',
                title='Work Submitted',
                message=f'{request.user.get_full_name()} has submitted work for "{project.title}"',
                link=f'/projects/{project.id}/'
            )
            
            messages.success(request, 'Work submitted successfully! Waiting for customer approval.')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectUpdateForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/submit_work.html', context)


@login_required
def complete_project(request, project_id):
    """Customer completes the project (final payment)"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_complete(request.user):
        messages.error(request, 'You cannot complete this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        project.status = 'completed'
        project.completed_at = timezone.now()
        project.save()
        
        # Update provider stats
        provider = project.provider
        provider.completed_projects += 1
        provider.total_earned += project.provider_payout
        provider.balance += project.provider_payout
        provider.save()
        
        ProjectActivity.objects.create(
            project=project,
            user=request.user,
            activity_type='status_change',
            description=f'Project completed by {request.user.get_full_name()}'
        )
        
        Notification.objects.create(
            user=project.provider,
            type='payment',
            title='Project Completed',
            message=f'Project "{project.title}" has been completed and payment released.',
            link=f'/projects/{project.id}/'
        )
        
        messages.success(request, 'Project completed! Payment has been released to the provider.')
        return redirect('projects:detail', project_id=project.id)
    
    return render(request, 'projects/complete.html', {'project': project})


@login_required
def cancel_project(request, project_id):
    """Cancel a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to cancel this project.')
        return redirect('projects:list')
    
    if project.status in ['completed', 'cancelled']:
        messages.error(request, 'This project cannot be cancelled.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        project.status = 'cancelled'
        project.save()
        
        ProjectActivity.objects.create(
            project=project,
            user=request.user,
            activity_type='status_change',
            description=f'Project cancelled by {request.user.get_full_name()}: {reason}'
        )
        
        other_user = project.provider if request.user == project.customer else project.customer
        Notification.objects.create(
            user=other_user,
            type='project',
            title='Project Cancelled',
            message=f'{request.user.get_full_name()} has cancelled the project "{project.title}"',
            link=f'/projects/{project.id}/'
        )
        
        messages.success(request, 'Project cancelled successfully.')
        return redirect('projects:list')
    
    context = {
        'project': project,
    }
    return render(request, 'projects/cancel.html', context)


@login_required
def pay_deposit(request, project_id):
    """Process deposit payment"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_pay_deposit(request.user):
        messages.error(request, 'Deposit payment is not available for this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'mpesa')
        
        try:
            from payments.services import PaymentService
            
            payment = PaymentService.process_deposit(
                project=project,
                method=payment_method,
                amount=project.deposit_amount
            )
            
            if payment['success']:
                project.deposit_paid = True
                project.deposit_payment_id = payment['transaction_id']
                project.deposit_paid_at = timezone.now()
                project.status = 'deposit_paid'
                project.save()
                
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    activity_type='payment',
                    description=f'Deposit payment of KSh {project.deposit_amount} made by {request.user.get_full_name()}'
                )
                
                Notification.objects.create(
                    user=project.provider,
                    type='payment',
                    title='Deposit Paid',
                    message=f'Customer has paid deposit of KSh {project.deposit_amount} for "{project.title}"',
                    link=f'/projects/{project.id}/'
                )
                
                messages.success(request, f'Deposit of KSh {project.deposit_amount} paid successfully!')
                return redirect('projects:detail', project_id=project.id)
            else:
                messages.error(request, f'Payment failed: {payment.get("error", "Unknown error")}')
                
        except Exception as e:
            messages.error(request, f'Payment error: {str(e)}')
    
    payment_methods = ['mpesa', 'airtel_money', 'stripe']
    
    context = {
        'project': project,
        'payment_methods': payment_methods,
        'amount': project.deposit_amount,
        'is_deposit': True,
    }
    return render(request, 'projects/pay.html', context)


@login_required
def pay_final(request, project_id):
    """Process final payment"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_pay_final(request.user):
        messages.error(request, 'Final payment is not available for this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'mpesa')
        
        try:
            from payments.services import PaymentService
            
            payment = PaymentService.process_final_payment(
                project=project,
                method=payment_method,
                amount=project.final_amount
            )
            
            if payment['success']:
                project.final_paid = True
                project.final_payment_id = payment['transaction_id']
                project.final_paid_at = timezone.now()
                project.status = 'completed'
                project.completed_at = timezone.now()
                project.save()
                
                # Update provider balance
                provider = project.provider
                provider.balance += project.provider_payout
                provider.total_earned += project.provider_payout
                provider.completed_projects += 1
                provider.save()
                
                ProjectActivity.objects.create(
                    project=project,
                    user=request.user,
                    activity_type='payment',
                    description=f'Final payment of KSh {project.final_amount} made by {request.user.get_full_name()}'
                )
                
                Notification.objects.create(
                    user=project.provider,
                    type='payment',
                    title='Final Payment Received',
                    message=f'Final payment of KSh {project.final_amount} received for "{project.title}"',
                    link=f'/projects/{project.id}/'
                )
                
                messages.success(request, f'Final payment of KSh {project.final_amount} paid successfully!')
                return redirect('projects:detail', project_id=project.id)
            else:
                messages.error(request, f'Payment failed: {payment.get("error", "Unknown error")}')
                
        except Exception as e:
            messages.error(request, f'Payment error: {str(e)}')
    
    payment_methods = ['mpesa', 'airtel_money', 'stripe']
    
    context = {
        'project': project,
        'payment_methods': payment_methods,
        'amount': project.final_amount,
        'platform_fee': project.platform_fee,
        'provider_payout': project.provider_payout,
        'is_deposit': False,
    }
    return render(request, 'projects/pay.html', context)


@login_required
def create_dispute(request, project_id):
    """Create a dispute for a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.can_dispute(request.user):
        messages.error(request, 'You cannot dispute this project.')
        return redirect('projects:detail', project_id=project.id)
    
    if request.method == 'POST':
        form = DisputeForm(request.POST, request.FILES)
        if form.is_valid():
            dispute = form.save(commit=False)
            dispute.project = project
            dispute.user = request.user
            dispute.save()
            
            project.status = 'disputed'
            project.dispute_reason = dispute.description[:200]
            project.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='dispute_raised',
                description=f'Dispute raised by {request.user.get_full_name()}: {dispute.title}'
            )
            
            other_user = project.provider if request.user == project.customer else project.customer
            Notification.objects.create(
                user=other_user,
                type='dispute',
                title='Dispute Raised',
                message=f'{request.user.get_full_name()} has raised a dispute on "{project.title}"',
                link=f'/projects/dispute/{dispute.id}/'
            )
            
            messages.success(request, 'Dispute raised successfully. Admin will review it.')
            return redirect('projects:dispute_detail', dispute_id=dispute.id)
    else:
        form = DisputeForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/create_dispute.html', context)


@login_required
def dispute_detail(request, dispute_id):
    """View dispute details"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    project = dispute.project
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to view this dispute.')
        return redirect('projects:list')
    
    if request.method == 'POST' and request.user.is_staff:
        # Admin resolving dispute
        resolution = request.POST.get('resolution')
        if resolution:
            dispute.resolve(request.user, resolution)
            
            Notification.objects.create(
                user=project.customer,
                type='dispute',
                title='Dispute Resolved',
                message=f'Dispute on "{project.title}" has been resolved.',
                link=f'/projects/{project.id}/'
            )
            Notification.objects.create(
                user=project.provider,
                type='dispute',
                title='Dispute Resolved',
                message=f'Dispute on "{project.title}" has been resolved.',
                link=f'/projects/{project.id}/'
            )
            
            messages.success(request, 'Dispute resolved successfully.')
            return redirect('projects:detail', project_id=project.id)
    
    context = {
        'dispute': dispute,
        'project': project,
        'is_admin': request.user.is_staff,
    }
    return render(request, 'projects/dispute_detail.html', context)


@login_required
def add_project_update(request, project_id):
    """Add an update to a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to update this project.')
        return redirect('projects:list')
    
    if request.method == 'POST':
        form = ProjectUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.project = project
            update.user = request.user
            update.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='message',
                description=f'Update added by {request.user.get_full_name()}'
            )
            
            other_user = project.provider if request.user == project.customer else project.customer
            Notification.objects.create(
                user=other_user,
                type='project',
                title='Project Update',
                message=f'{request.user.get_full_name()} added an update to "{project.title}"',
                link=f'/projects/{project.id}/'
            )
            
            messages.success(request, 'Update added successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectUpdateForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/add_update.html', context)


@login_required
def project_messages(request, project_id):
    """View messages for a project (redirect to chat)"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to view messages.')
        return redirect('projects:list')
    
    # Get or create conversation
    from chat.models import Conversation
    conversation, created = Conversation.objects.get_or_create(
        project_id=project.id,
        defaults={'is_active': True}
    )
    
    if created:
        conversation.participants.add(project.customer, project.provider)
    
    return redirect('chat:detail', conversation_id=conversation.id)


@login_required
def add_milestone(request, project_id):
    """Add a milestone to a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to add milestones.')
        return redirect('projects:list')
    
    if request.method == 'POST':
        form = ProjectMilestoneForm(request.POST, request.FILES)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.project = project
            milestone.save()
            
            messages.success(request, 'Milestone added successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectMilestoneForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/add_milestone.html', context)


@login_required
@require_POST
def complete_milestone(request, milestone_id):
    """Mark a milestone as completed"""
    milestone = get_object_or_404(ProjectMilestone, id=milestone_id)
    project = milestone.project
    
    if request.user not in [project.customer, project.provider]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    milestone.complete()
    
    ProjectActivity.objects.create(
        project=project,
        user=request.user,
        activity_type='milestone_completed',
        description=f'Milestone "{milestone.title}" completed by {request.user.get_full_name()}'
    )
    
    return JsonResponse({'success': True})


@login_required
def upload_document(request, project_id):
    """Upload a document to a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to upload documents.')
        return redirect('projects:list')
    
    if request.method == 'POST':
        form = ProjectDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.project = project
            document.user = request.user
            document.save()
            
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='file_upload',
                description=f'Document "{document.title}" uploaded by {request.user.get_full_name()}'
            )
            
            messages.success(request, 'Document uploaded successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectDocumentForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/upload_document.html', context)


@login_required
def invite_provider(request, project_id):
    """Invite a provider to a project"""
    project = get_object_or_404(Project, id=project_id, customer=request.user)
    
    if request.method == 'POST':
        form = ProjectInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['recipient_email']
            message = form.cleaned_data.get('message', '')
            
            try:
                recipient = User.objects.get(email=email)
                
                # Check if already invited
                existing = ProjectInvitation.objects.filter(
                    project=project,
                    recipient=recipient,
                    status='pending'
                ).exists()
                
                if existing:
                    messages.warning(request, 'This provider has already been invited.')
                    return redirect('projects:detail', project_id=project.id)
                
                # Create invitation
                invitation = ProjectInvitation.objects.create(
                    project=project,
                    sender=request.user,
                    recipient=recipient,
                    message=message,
                    expires_at=timezone.now() + timezone.timedelta(days=7)
                )
                
                Notification.objects.create(
                    user=recipient,
                    type='project',
                    title='Project Invitation',
                    message=f'You have been invited to work on "{project.title}" by {request.user.get_full_name()}',
                    link=f'/projects/invitation/{invitation.id}/'
                )
                
                messages.success(request, f'Invitation sent to {recipient.get_full_name()}!')
                
            except User.DoesNotExist:
                messages.error(request, 'User with this email does not exist.')
    else:
        form = ProjectInvitationForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'projects/invite_provider.html', context)


@login_required
def handle_invitation(request, invitation_id):
    """Handle project invitation response"""
    invitation = get_object_or_404(ProjectInvitation, id=invitation_id, recipient=request.user)
    
    if invitation.is_expired():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'This invitation has expired.')
        return redirect('projects:list')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            invitation.accept()
            messages.success(request, f'You have accepted the invitation to work on "{invitation.project.title}".')
            return redirect('projects:detail', project_id=invitation.project.id)
        elif action == 'decline':
            invitation.decline()
            messages.info(request, 'You have declined the invitation.')
            return redirect('projects:list')
    
    context = {
        'invitation': invitation,
    }
    return render(request, 'projects/invitation_handle.html', context)


@login_required
def project_statistics(request):
    """View project statistics for the user"""
    user = request.user
    
    # Projects statistics
    total_projects = Project.objects.filter(Q(customer=user) | Q(provider=user)).count()
    active_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user),
        status__in=['agreed', 'deposit_paid', 'in_progress', 'submitted']
    ).count()
    completed_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user),
        status='completed'
    ).count()
    
    # Earnings (for providers)
    total_earnings = 0
    if user.is_provider():
        total_earnings = Project.objects.filter(
            provider=user,
            status='completed'
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0
    
    # Spending (for customers)
    total_spent = 0
    if user.is_customer():
        total_spent = Project.objects.filter(
            customer=user,
            status='completed'
        ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0
    
    # Monthly data for charts
    from django.db.models.functions import TruncMonth
    monthly_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_earnings': total_earnings,
        'total_spent': total_spent,
        'monthly_projects': monthly_projects,
    }
    return render(request, 'projects/statistics.html', context)