# projects/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import json

from .models import (
    Project, ProjectUpdate, Dispute, ProjectMilestone,
    ProjectDocument, ProjectActivity, ProjectInvitation,
    Order, OrderLineItem, OrderInspiration, OrderStatusLog,
)
from .forms import (
    ProjectForm, ProjectUpdateForm, DisputeForm,
    ProjectMilestoneForm, ProjectDocumentForm,
    ProjectInvitationForm, ProjectFilterForm,
    OrderForm, OrderInspirationForm, OrderLineItemFormSet,
    OrderDeclineForm, OrderCancelForm,
)
from services.models import Service, ServicePortfolio
from accounts.models import User
from notifications.models import Notification


# ============================================================
# LEGACY PROJECT VIEWS (unchanged)
# ============================================================

@login_required
def project_list(request):
    user = request.user
    projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user)
    ).select_related('customer', 'provider', 'service')

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

    paginator = Paginator(projects, 10)
    page = request.GET.get('page')

    try:
        projects = paginator.page(page)
    except PageNotAnInteger:
        projects = paginator.page(1)
    except EmptyPage:
        projects = paginator.page(paginator.num_pages)

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
    return redirect('projects:list')


@login_required
def project_create(request, service_id):
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
            project.agreed_price = form.cleaned_data['agreed_price']
            project.deposit_percentage = service.deposit_percentage
            project.deposit_amount = project.calculate_deposit()
            project.final_amount = project.agreed_price - project.deposit_amount
            project.platform_fee = project.calculate_platform_fee()
            project.provider_payout = project.calculate_provider_payout()
            project.status = 'negotiating'
            project.save()

            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='created',
                description=f'Project created by {request.user.get_full_name()}'
            )
            Notification.objects.create(
                user=service.provider,
                type='project',
                title='New Project Request',
                message=f'{request.user.get_full_name()} wants to hire you for "{project.title}"',
                link=f'/projects/{project.id}/'
            )

            messages.success(request, 'Project created successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectForm(initial={'agreed_price': service.price_min})

    return render(request, 'projects/create.html', {'form': form, 'service': service})


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized to view this project.')
        return redirect('projects:list')

    updates = project.updates.all().order_by('-created_at')[:10]
    milestones = project.milestones.all().order_by('order', 'due_date')
    documents = project.documents.all().order_by('-created_at')
    activities = project.activities.all().order_by('-created_at')[:20]

    try:
        from chat.models import Conversation
        conversation = Conversation.objects.get(project_id=project.id)
    except Exception:
        conversation = None

    can_review = False
    if project.status == 'completed' and request.user == project.customer:
        from reviews.models import Review
        can_review = not Review.objects.filter(project_id=project.id).exists()

    context = {
        'project': project,
        'updates': updates,
        'milestones': milestones,
        'documents': documents,
        'activities': activities,
        'conversation': conversation,
        'can_review': can_review,
        'is_customer': request.user == project.customer,
        'is_provider': request.user == project.provider,
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
    project = get_object_or_404(Project, id=project_id)
    if not project.can_edit(request.user):
        messages.error(request, 'You cannot edit this project.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            ProjectActivity.objects.create(
                project=project, user=request.user,
                activity_type='updated',
                description=f'Project updated by {request.user.get_full_name()}'
            )
            messages.success(request, 'Project updated successfully!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/edit.html', {'form': form, 'project': project})


@login_required
def project_delete(request, project_id):
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
    project = get_object_or_404(Project, id=project_id)
    if not project.can_accept(request.user):
        messages.error(request, 'You cannot accept this project.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        project.status = 'agreed'
        project.agreed_at = timezone.now()
        project.save()
        ProjectActivity.objects.create(
            project=project, user=request.user,
            activity_type='status_change',
            description=f'Project accepted by {request.user.get_full_name()}'
        )
        Notification.objects.create(
            user=project.customer, type='project',
            title='Project Accepted',
            message=f'{request.user.get_full_name()} accepted your project.',
            link=f'/projects/{project.id}/'
        )
        messages.success(request, 'Project accepted!')
        return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/accept.html', {'project': project})


@login_required
def start_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not project.can_start(request.user):
        messages.error(request, 'You cannot start this project.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        project.status = 'in_progress'
        project.started_at = timezone.now()
        project.save()
        ProjectActivity.objects.create(
            project=project, user=request.user,
            activity_type='status_change',
            description=f'Work started by {request.user.get_full_name()}'
        )
        messages.success(request, 'Project started!')
        return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/start.html', {'project': project})


@login_required
def submit_work(request, project_id):
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
            messages.success(request, 'Work submitted!')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectUpdateForm()

    return render(request, 'projects/submit_work.html', {'form': form, 'project': project})


@login_required
def complete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not project.can_complete(request.user):
        messages.error(request, 'You cannot complete this project.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        project.status = 'completed'
        project.completed_at = timezone.now()
        project.save()

        provider = project.provider
        provider.completed_projects += 1
        provider.total_earned += project.provider_payout
        provider.balance += project.provider_payout
        provider.save()

        messages.success(request, 'Project completed!')
        return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/complete.html', {'project': project})


@login_required
def cancel_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not authorized.')
        return redirect('projects:list')

    if project.status in ['completed', 'cancelled']:
        messages.error(request, 'This project cannot be cancelled.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        project.status = 'cancelled'
        project.save()
        ProjectActivity.objects.create(
            project=project, user=request.user,
            activity_type='status_change',
            description=f'Project cancelled: {reason}'
        )
        messages.success(request, 'Project cancelled.')
        return redirect('projects:list')

    return render(request, 'projects/cancel.html', {'project': project})


# ============================================================
# PAYMENT STUBS (legacy Project)
# ============================================================

@login_required
def pay_deposit(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not project.can_pay_deposit(request.user):
        messages.error(request, 'Deposit payment is not available.')
        return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/pay.html', {
        'project': project,
        'amount': project.deposit_amount,
        'is_deposit': True,
    })


@login_required
def pay_final(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not project.can_pay_final(request.user):
        messages.error(request, 'Final payment is not available.')
        return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/pay.html', {
        'project': project,
        'amount': project.final_amount,
        'is_deposit': False,
    })


# ============================================================
# DISPUTES / UPDATES (legacy)
# ============================================================

@login_required
def create_dispute(request, project_id):
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
            project.save()
            messages.success(request, 'Dispute raised.')
            return redirect('projects:dispute_detail', dispute_id=dispute.id)
    else:
        form = DisputeForm()

    return render(request, 'projects/create_dispute.html', {'form': form, 'project': project})


@login_required
def dispute_detail(request, dispute_id):
    dispute = get_object_or_404(Dispute, id=dispute_id)
    project = dispute.project
    if request.user not in [project.customer, project.provider] and not request.user.is_staff:
        messages.error(request, 'Unauthorized.')
        return redirect('projects:list')

    if request.method == 'POST' and request.user.is_staff:
        resolution = request.POST.get('resolution')
        if resolution:
            dispute.resolve(request.user, resolution)
            messages.success(request, 'Dispute resolved.')
            return redirect('projects:detail', project_id=project.id)

    return render(request, 'projects/dispute_detail.html', {
        'dispute': dispute, 'project': project, 'is_admin': request.user.is_staff,
    })


@login_required
def add_project_update(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'Unauthorized.')
        return redirect('projects:list')

    if request.method == 'POST':
        form = ProjectUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.project = project
            update.user = request.user
            update.save()
            messages.success(request, 'Update added.')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectUpdateForm()

    return render(request, 'projects/add_update.html', {'form': form, 'project': project})


@login_required
def project_messages(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'Unauthorized.')
        return redirect('projects:list')

    from chat.models import Conversation
    conversation, created = Conversation.objects.get_or_create(
        project_id=project.id, defaults={'is_active': True}
    )
    if created:
        conversation.participants.add(project.customer, project.provider)

    return redirect('chat:detail', conversation_id=conversation.id)


@login_required
def add_milestone(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'Unauthorized.')
        return redirect('projects:list')

    if request.method == 'POST':
        form = ProjectMilestoneForm(request.POST, request.FILES)
        if form.is_valid():
            m = form.save(commit=False)
            m.project = project
            m.save()
            messages.success(request, 'Milestone added.')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectMilestoneForm()

    return render(request, 'projects/add_milestone.html', {'form': form, 'project': project})


@login_required
@require_POST
def complete_milestone(request, milestone_id):
    m = get_object_or_404(ProjectMilestone, id=milestone_id)
    project = m.project
    if request.user not in [project.customer, project.provider]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    m.complete()
    return JsonResponse({'success': True})


@login_required
def upload_document(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'Unauthorized.')
        return redirect('projects:list')

    if request.method == 'POST':
        form = ProjectDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.save(commit=False)
            d.project = project
            d.user = request.user
            d.save()
            messages.success(request, 'Document uploaded.')
            return redirect('projects:detail', project_id=project.id)
    else:
        form = ProjectDocumentForm()

    return render(request, 'projects/upload_document.html', {'form': form, 'project': project})


@login_required
def invite_provider(request, project_id):
    project = get_object_or_404(Project, id=project_id, customer=request.user)

    if request.method == 'POST':
        form = ProjectInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['recipient_email']
            message = form.cleaned_data.get('message', '')
            try:
                recipient = User.objects.get(email=email)
                ProjectInvitation.objects.create(
                    project=project,
                    sender=request.user,
                    recipient=recipient,
                    message=message,
                    expires_at=timezone.now() + timezone.timedelta(days=7),
                )
                messages.success(request, f'Invitation sent to {recipient.get_full_name()}.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
    else:
        form = ProjectInvitationForm()

    return render(request, 'projects/invite_provider.html', {'form': form, 'project': project})


@login_required
def handle_invitation(request, invitation_id):
    invitation = get_object_or_404(ProjectInvitation, id=invitation_id, recipient=request.user)
    if invitation.is_expired():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Invitation expired.')
        return redirect('projects:list')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            invitation.accept()
            messages.success(request, 'Invitation accepted.')
            return redirect('projects:detail', project_id=invitation.project.id)
        elif action == 'decline':
            invitation.decline()
            messages.info(request, 'Invitation declined.')
            return redirect('projects:list')

    return render(request, 'projects/invitation_handle.html', {'invitation': invitation})


@login_required
def project_statistics(request):
    user = request.user
    total_projects = Project.objects.filter(Q(customer=user) | Q(provider=user)).count()
    active_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user),
        status__in=['agreed', 'deposit_paid', 'in_progress', 'submitted']
    ).count()
    completed_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user), status='completed'
    ).count()

    total_earnings = 0
    if user.is_provider():
        total_earnings = Project.objects.filter(
            provider=user, status='completed'
        ).aggregate(Sum('provider_payout'))['provider_payout__sum'] or 0

    total_spent = 0
    if user.is_customer():
        total_spent = Project.objects.filter(
            customer=user, status='completed'
        ).aggregate(Sum('agreed_price'))['agreed_price__sum'] or 0

    from django.db.models.functions import TruncMonth
    monthly_projects = Project.objects.filter(
        Q(customer=user) | Q(provider=user)
    ).annotate(month=TruncMonth('created_at')).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    return render(request, 'projects/statistics.html', {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_earnings': total_earnings,
        'total_spent': total_spent,
        'monthly_projects': monthly_projects,
    })


# ============================================================
# ORDER VIEWS — Phase 3A
# ============================================================

@login_required
def order_create(request, service_id):
    """
    Client creates an order from a specific service.
    Restricted to services the current user doesn't own.
    """
    service = get_object_or_404(
        Service.objects.select_related('provider', 'category'),
        id=service_id,
        is_active=True
    )

    if request.user == service.provider:
        messages.error(request, "You can't order your own service.")
        return redirect('services:detail', service_id=service.id)

    # Portfolio samples for the fundi's services (option B — all fundi's works)
    samples = ServicePortfolio.objects.filter(
        service__provider=service.provider,
        service__is_active=True,
        image__isnull=False,
    ).exclude(image='').select_related('service').order_by('-is_cover', '-created_at')[:12]

    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        inspiration_images = request.FILES.getlist('inspiration_images')
        inspiration_notes = request.POST.getlist('inspiration_notes')

        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.customer = request.user
                order.provider = service.provider
                order.service = service

                # Selected sample (optional)
                sample_id = form.cleaned_data.get('selected_sample_id')
                if sample_id:
                    try:
                        order.selected_sample = ServicePortfolio.objects.get(
                            id=sample_id, service__provider=service.provider
                        )
                    except ServicePortfolio.DoesNotExist:
                        pass

                # Disclaimer required
                disclaimer = request.POST.get('disclaimer_accepted')
                if disclaimer:
                    order.disclaimer_accepted = True
                    order.disclaimer_accepted_at = timezone.now()

                order.estimated_days = None  # set by provider on accept
                order.deposit_percent = Decimal(str(
                    getattr(settings, 'DEPOSIT_DEFAULT_PERCENTAGE', 30)
                ))
                order.status = 'pending_acceptance'
                order.save()
                order.recalculate_fees()

                # Inspiration images (up to 3)
                for idx, img in enumerate(inspiration_images[:3]):
                    if img:
                        note = inspiration_notes[idx] if idx < len(inspiration_notes) else ''
                        OrderInspiration.objects.create(
                            order=order, image=img, note=note
                        )

                OrderStatusLog.objects.create(
                    order=order, user=request.user,
                    from_status='', to_status='pending_acceptance',
                    note='Order submitted by client.'
                )

                # Notify provider
                try:
                    Notification.objects.create(
                        user=service.provider,
                        type='project',
                        title='New Order Received',
                        message=f'{request.user.get_full_name()} sent you an order: "{order.title}"',
                        link=f'/projects/orders/{order.id}/'
                    )
                except Exception:
                    pass

            messages.success(
                request,
                "Order sent! You'll be notified when the fundi responds."
            )
            return redirect('projects:order_detail', order_id=order.id)
    else:
        form = OrderForm(initial={
            'agreed_price': service.price_min,
            'materials_mode': 'fundi_provides',
        })

    context = {
        'form': form,
        'service': service,
        'samples': samples,
        'platform_fee_pct': settings.PLATFORM_FEE_PERCENTAGE,
        'escrow_fee_pct': settings.ESCROW_SERVICE_FEE_PERCENTAGE,
        'deposit_pct': settings.DEPOSIT_DEFAULT_PERCENTAGE,
    }
    return render(request, 'projects/order_form.html', context)


@login_required
def order_detail(request, order_id):
    """
    Order detail page. Shows the quotation breakdown, milestones,
    line items, inspo images, and the actions the current user can take.
    """
    order = get_object_or_404(
        Order.objects.select_related(
            'customer', 'provider', 'service', 'selected_sample'
        ),
        id=order_id,
    )

    if not order.can_be_viewed_by(request.user):
        messages.error(request, "You don't have access to this order.")
        return redirect('projects:list')

    line_items = order.line_items.all()
    inspirations = order.inspirations.all()
    status_logs = order.status_logs.select_related('user').order_by('-created_at')[:30]

    is_customer = request.user == order.customer
    is_provider = request.user == order.provider

    context = {
        'order': order,
        'line_items': line_items,
        'inspirations': inspirations,
        'status_logs': status_logs,
        'is_customer': is_customer,
        'is_provider': is_provider,
        'can_accept': order.can_accept(request.user),
        'can_decline': order.can_decline(request.user),
        'can_cancel': order.can_cancel(request.user),
        'can_pay_deposit': order.can_pay_deposit(request.user),
        'can_start': order.can_start(request.user),
        'can_request_milestone': order.can_request_milestone(request.user),
        'can_view_milestone': order.can_view_milestone(request.user),
        'can_submit': order.can_submit(request.user),
        'can_approve': order.can_approve(request.user),
        'can_dispute': order.can_dispute(request.user),
        'decline_form': OrderDeclineForm(),
        'cancel_form': OrderCancelForm(),
    }
    return render(request, 'projects/order_detail.html', context)


@login_required
@require_POST
def order_accept(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not order.can_accept(request.user):
        messages.error(request, "You can't accept this order.")
        return redirect('projects:order_detail', order_id=order.id)

    estimated_days_raw = request.POST.get('estimated_days', '').strip()
    if estimated_days_raw.isdigit():
        order.estimated_days = int(estimated_days_raw)

    # Optional: provider adjusts the price
    new_price_raw = request.POST.get('agreed_price', '').strip()
    if new_price_raw:
        try:
            new_price = Decimal(new_price_raw)
            if new_price >= 100:
                order.agreed_price = new_price
        except Exception:
            pass

    with transaction.atomic():
        prev = order.status
        order.status = 'accepted'
        order.accepted_at = timezone.now()
        order.save()
        order.recalculate_fees()

        OrderStatusLog.objects.create(
            order=order, user=request.user,
            from_status=prev, to_status='accepted',
            note=f'Accepted by fundi. Estimated {order.estimated_days or "n/a"} days.'
        )

    try:
        Notification.objects.create(
            user=order.customer, type='project',
            title='Order Accepted',
            message=f'{request.user.get_full_name()} accepted your order. Pay the deposit to start.',
            link=f'/projects/orders/{order.id}/'
        )
    except Exception:
        pass

    messages.success(request, 'Order accepted. The client has been notified to pay the deposit.')
    return redirect('projects:order_detail', order_id=order.id)


@login_required
@require_POST
def order_decline(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not order.can_decline(request.user):
        messages.error(request, "You can't decline this order.")
        return redirect('projects:order_detail', order_id=order.id)

    form = OrderDeclineForm(request.POST)
    reason = form.cleaned_data.get('reason', '') if form.is_valid() else ''

    with transaction.atomic():
        prev = order.status
        order.status = 'declined'
        order.declined_at = timezone.now()
        order.decline_reason = reason
        order.save()
        OrderStatusLog.objects.create(
            order=order, user=request.user,
            from_status=prev, to_status='declined',
            note=reason or 'Declined by fundi.'
        )

    try:
        Notification.objects.create(
            user=order.customer, type='project',
            title='Order Declined',
            message=f'{request.user.get_full_name()} declined your order.',
            link=f'/projects/orders/{order.id}/'
        )
    except Exception:
        pass

    messages.info(request, 'Order declined.')
    return redirect('projects:order_detail', order_id=order.id)


@login_required
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not order.can_cancel(request.user):
        messages.error(request, "You can't cancel this order.")
        return redirect('projects:order_detail', order_id=order.id)

    form = OrderCancelForm(request.POST)
    reason = form.cleaned_data.get('reason', '') if form.is_valid() else ''

    with transaction.atomic():
        prev = order.status
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancel_reason = reason
        order.save()
        OrderStatusLog.objects.create(
            order=order, user=request.user,
            from_status=prev, to_status='cancelled',
            note=reason or 'Cancelled by client.'
        )

    try:
        Notification.objects.create(
            user=order.provider, type='project',
            title='Order Cancelled',
            message=f'{request.user.get_full_name()} cancelled the order "{order.title}".',
            link=f'/projects/orders/{order.id}/'
        )
    except Exception:
        pass

    messages.info(request, 'Order cancelled.')
    return redirect('projects:order_detail', order_id=order.id)