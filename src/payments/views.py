# payments/views.py
import json
import logging
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.conf import settings

from accounts.models import Wallet, WalletTransaction
from .models import PaymentMethod, PaymentTransaction, Payout
from .forms import (
    PaymentMethodForm, PayoutRequestForm,
    WalletDepositForm, WalletWithdrawForm,
)
from projects.models import Project, Order, OrderStatusLog
from notifications.models import Notification

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def _log_status(order, user, from_status, to_status, note=''):
    OrderStatusLog.objects.create(
        order=order, user=user,
        from_status=from_status, to_status=to_status, note=note,
    )


# ============================================================
# PAYMENT DASHBOARD
# ============================================================

@login_required
def payment_dashboard(request):
    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user)

    transactions = PaymentTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:10]

    pending_payments = PaymentTransaction.objects.filter(
        user=user, status='pending'
    ).count()

    total_spent = PaymentTransaction.objects.filter(
        user=user, status='completed',
        payment_type__in=['deposit', 'final', 'order_deposit', 'order_balance']
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_earnings = 0
    if user.is_provider():
        total_earnings = PaymentTransaction.objects.filter(
            user=user, status='completed', payment_type='payout'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'wallet': wallet,
        'transactions': transactions,
        'pending_payments': pending_payments,
        'total_spent': total_spent,
        'total_earnings': total_earnings,
    }
    return render(request, 'payments/dashboard.html', context)


# ============================================================
# ORDER DEPOSIT — Phase 3B
# ============================================================

@login_required
def process_order_deposit(request, order_id):
    """
    Initiate deposit payment for an Order via M-PESA STK Push.
    """
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if not order.can_pay_deposit(request.user):
        messages.error(request, 'Deposit payment is not available for this order.')
        return redirect('projects:order_detail', order_id=order.id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'mpesa')
        phone_number = request.POST.get('phone_number', '').strip()

        # ---- Wallet path ----
        if payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= order.deposit_amount:
                with transaction.atomic():
                    wallet.deduct_balance(
                        order.deposit_amount,
                        transaction_type='payment',
                        description=f'Order #{order.id} deposit'
                    )

                    tx = PaymentTransaction.objects.create(
                        order=order,
                        user=request.user,
                        payment_type='order_deposit',
                        payment_method='wallet',
                        amount=order.deposit_amount,
                        platform_fee=0,
                        net_amount=order.deposit_amount,
                        status='completed',
                        completed_at=timezone.now(),
                        is_escrow_held=True,
                    )

                    prev = order.status
                    order.deposit_paid = True
                    order.deposit_payment_id = f"WALLET-{tx.id}"
                    order.deposit_paid_at = timezone.now()
                    order.status = 'deposit_paid'
                    order.save()

                    _log_status(
                        order, request.user, prev, 'deposit_paid',
                        'Deposit paid from wallet.'
                    )

                    # Flip phone_public if needed
                    try:
                        order.provider.provider_profile.flip_phone_public_if_needed()
                    except Exception:
                        pass

                messages.success(
                    request,
                    f'Deposit of KSh {order.deposit_amount:,.0f} paid from wallet.'
                )
                return redirect('projects:order_detail', order_id=order.id)
            else:
                messages.error(request, 'Insufficient wallet balance.')
                return redirect('payments:process_order_deposit', order_id=order.id)

        # ---- M-PESA path ----
        if not phone_number:
            messages.error(request, 'Phone number is required for M-PESA.')
            return redirect('payments:process_order_deposit', order_id=order.id)

        from .services import MpesaService
        mpesa = MpesaService()

        callback_url = request.build_absolute_uri('/payments/mpesa/callback/')
        result = mpesa.stk_push(
            phone_number=phone_number,
            amount=float(order.deposit_amount),
            account_reference=f"ORD{order.id}",
            transaction_desc=f"Deposit for order {order.id}",
            callback_url=callback_url,
        )

        if not result.get('success'):
            messages.error(
                request,
                f"M-PESA failed: {result.get('error', 'Unknown error')}"
            )
            return redirect('payments:process_order_deposit', order_id=order.id)

        # Record the pending transaction
        tx = PaymentTransaction.objects.create(
            order=order,
            user=request.user,
            payment_type='order_deposit',
            payment_method='mpesa',
            amount=order.deposit_amount,
            platform_fee=0,
            net_amount=order.deposit_amount,
            checkout_request_id=result['checkout_request_id'],
            mpesa_phone=phone_number,
            status='processing',
            is_escrow_held=True,
            metadata={
                'checkout_request_id': result['checkout_request_id'],
                'merchant_request_id': result.get('merchant_request_id'),
                'mock': result.get('mock', False),
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        messages.info(
            request,
            'M-PESA prompt sent. Please enter your PIN on your phone.'
        )
        return redirect(
            'payments:order_payment_waiting',
            order_id=order.id,
            tx_id=tx.id,
        )

    # ---- GET: render payment selection page ----
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    context = {
        'order': order,
        'amount': order.deposit_amount,
        'wallet': wallet,
        'default_phone': request.user.phone_number or request.user.mpesa_phone or '',
        'mpesa_mock': getattr(settings, 'MPESA_MOCK', False),
    }
    return render(request, 'payments/order_deposit.html', context)


# ============================================================
# ORDER PAYMENT — waiting + polling
# ============================================================

@login_required
def order_payment_waiting(request, order_id, tx_id):
    """
    Page shown after STK Push is sent. Frontend polls the status
    endpoint until the transaction is complete or fails.
    """
    order = get_object_or_404(Order, id=order_id)
    if not order.can_be_viewed_by(request.user):
        messages.error(request, 'You do not have access to this order.')
        return redirect('projects:list')

    tx = get_object_or_404(PaymentTransaction, id=tx_id, order=order)

    context = {
        'order': order,
        'transaction': tx,
        'status_url': f"/payments/orders/{order.id}/status/{tx.id}/",
        'return_url': f"/projects/orders/{order.id}/",
        'mpesa_mock': getattr(settings, 'MPESA_MOCK', False),
    }
    return render(request, 'payments/order_waiting.html', context)


@login_required
def check_order_payment_status(request, order_id, tx_id):
    """
    JSON endpoint: polls M-PESA (or mock) for the transaction status,
    updates the PaymentTransaction + Order if complete.
    """
    order = get_object_or_404(Order, id=order_id)
    if not order.can_be_viewed_by(request.user):
        return JsonResponse({'error': 'forbidden'}, status=403)

    tx = get_object_or_404(PaymentTransaction, id=tx_id, order=order)

    # If already settled, return immediately
    if tx.status == 'completed':
        return JsonResponse({
            'status': 'completed',
            'receipt': tx.mpesa_receipt or '',
            'redirect': f'/projects/orders/{order.id}/',
        })
    if tx.status == 'failed':
        return JsonResponse({
            'status': 'failed',
            'reason': tx.status_reason or 'Payment failed.',
        })

    # Ask M-PESA
    from .services import MpesaService
    mpesa = MpesaService()
    result = mpesa.query_status(tx.checkout_request_id)

    if not result.get('success'):
        return JsonResponse({
            'status': 'processing',
            'note': result.get('error', ''),
        })

    result_code = str(result.get('result_code', ''))

    # Success
    if result_code == '0':
        with transaction.atomic():
            tx.mark_completed(receipt=result.get('mpesa_receipt'))
            if tx.mpesa_receipt is None:
                tx.mpesa_receipt = result.get('mpesa_receipt')
                tx.save(update_fields=['mpesa_receipt'])

            prev = order.status
            order.deposit_paid = True
            order.deposit_payment_id = result.get('mpesa_receipt')
            order.deposit_paid_at = timezone.now()
            order.status = 'deposit_paid'
            order.save()

            _log_status(
                order, request.user, prev, 'deposit_paid',
                f'Deposit paid via M-PESA. Receipt: {result.get("mpesa_receipt")}'
            )

            # Flip phone_public if needed
            try:
                order.provider.provider_profile.flip_phone_public_if_needed()
            except Exception:
                pass

            # Notify provider
            try:
                Notification.objects.create(
                    user=order.provider,
                    type='payment',
                    title='Deposit Received',
                    message=(
                        f'Deposit of KSh {order.deposit_amount:,.0f} received '
                        f'for order #{order.id}.'
                    ),
                    link=f'/projects/orders/{order.id}/',
                )
            except Exception:
                pass

        return JsonResponse({
            'status': 'completed',
            'receipt': result.get('mpesa_receipt') or '',
            'redirect': f'/projects/orders/{order.id}/',
        })

    # Cancelled by user (1032) or failed
    if result_code in ('1032', '1037', '2001'):
        tx.status = 'failed'
        tx.status_reason = result.get('result_desc') or 'Cancelled or timed out.'
        tx.save(update_fields=['status', 'status_reason', 'updated_at'])
        return JsonResponse({
            'status': 'failed',
            'reason': tx.status_reason,
        })

    # Still pending
    return JsonResponse({
        'status': 'processing',
        'note': result.get('result_desc', ''),
    })


# ============================================================
# ORDER BALANCE RELEASE (credit fundi wallet)
# ============================================================

@login_required
@require_POST
def release_order_balance(request, order_id):
    """
    Client approves completed work → we credit the fundi's wallet
    with provider_payout. No M-PESA transfer occurs here.
    """
    order = get_object_or_404(Order, id=order_id)

    if not order.can_approve(request.user):
        messages.error(request, 'You cannot approve this order yet.')
        return redirect('projects:order_detail', order_id=order.id)

    with transaction.atomic():
        # Ledger entry — balance paid by client
        PaymentTransaction.objects.create(
            order=order,
            user=order.customer,
            payment_type='order_balance',
            payment_method='internal',
            amount=order.balance_amount,
            platform_fee=order.platform_fee,
            net_amount=order.provider_payout,
            status='completed',
            completed_at=timezone.now(),
            is_escrow_held=False,
        )

        # Ledger entry — balance released to fundi's wallet
        release_tx = PaymentTransaction.objects.create(
            order=order,
            user=order.provider,
            payment_type='order_release',
            payment_method='internal',
            amount=order.provider_payout,
            platform_fee=0,
            net_amount=order.provider_payout,
            status='completed',
            completed_at=timezone.now(),
            is_escrow_held=False,
            escrow_released_at=timezone.now(),
        )

        # Release escrow on the original deposit tx
        PaymentTransaction.objects.filter(
            order=order, payment_type='order_deposit', is_escrow_held=True
        ).update(is_escrow_held=False, escrow_released_at=timezone.now())

        # Credit fundi wallet
        fundi_wallet, _ = Wallet.objects.get_or_create(user=order.provider)
        fundi_wallet.add_balance(
            order.provider_payout,
            transaction_type='earning',
            description=f'Escrow release — order #{order.id}: {order.title}',
        )

        # Update provider stats
        provider = order.provider
        provider.completed_projects = (provider.completed_projects or 0) + 1
        provider.total_earned = (provider.total_earned or 0) + order.provider_payout
        provider.save(update_fields=[
            'completed_projects', 'total_earned', 'updated_at'
        ])

        # Status → completed
        prev = order.status
        order.status = 'completed'
        order.balance_paid = True
        order.balance_payment_id = f"RELEASE-{release_tx.id}"
        order.balance_paid_at = timezone.now()
        order.completed_at = timezone.now()
        order.save()

        _log_status(
            order, request.user, prev, 'completed',
            f'Client approved. KSh {order.provider_payout:,.0f} released to fundi wallet.'
        )

        # Notify fundi
        try:
            Notification.objects.create(
                user=order.provider,
                type='payment',
                title='Payment Released',
                message=(
                    f'KSh {order.provider_payout:,.0f} added to your wallet for '
                    f'order #{order.id}. Withdrawals are processed within 24 hours.'
                ),
                link=f'/projects/orders/{order.id}/',
            )
        except Exception:
            pass

    messages.success(
        request,
        f'Order complete. KSh {order.provider_payout:,.0f} credited to the fundi\'s wallet.'
    )
    return redirect('projects:order_detail', order_id=order.id)


# ============================================================
# LEGACY PROJECT PAYMENT FLOWS (unchanged)
# ============================================================

@login_required
def process_deposit(request, project_id):
    project = get_object_or_404(Project, id=project_id, customer=request.user)

    if project.deposit_paid:
        messages.warning(request, 'Deposit already paid.')
        return redirect('projects:detail', project_id=project.id)

    if project.status != 'agreed':
        messages.error(request, 'Deposit cannot be processed for this project.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '')

        if payment_method == 'mpesa':
            from .services import MpesaService
            mpesa = MpesaService()
            result = mpesa.stk_push(
                phone_number=phone_number,
                amount=float(project.deposit_amount),
                account_reference=f"DEP-{project.id}",
                transaction_desc=f"Deposit for {project.title}",
                callback_url=request.build_absolute_uri('/payments/mpesa/callback/')
            )

            if result['success']:
                tx = PaymentTransaction.objects.create(
                    project=project,
                    user=request.user,
                    payment_type='deposit',
                    payment_method='mpesa',
                    amount=project.deposit_amount,
                    platform_fee=0,
                    net_amount=project.deposit_amount,
                    checkout_request_id=result['checkout_request_id'],
                    mpesa_phone=phone_number,
                    status='processing',
                    metadata={
                        'checkout_request_id': result['checkout_request_id'],
                        'merchant_request_id': result.get('merchant_request_id'),
                        'mock': result.get('mock', False),
                    }
                )
                messages.info(request, 'M-PESA prompt sent. Enter your PIN.')
                return redirect('payments:mpesa_query', checkout_id=result['checkout_request_id'])
            else:
                messages.error(request, f"M-PESA failed: {result.get('error')}")

        elif payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= project.deposit_amount:
                wallet.deduct_balance(
                    project.deposit_amount,
                    transaction_type='payment',
                    description=f'Deposit for project: {project.title}'
                )
                PaymentTransaction.objects.create(
                    project=project, user=request.user,
                    payment_type='deposit', payment_method='wallet',
                    amount=project.deposit_amount, platform_fee=0,
                    net_amount=project.deposit_amount,
                    status='completed', completed_at=timezone.now(),
                )
                project.deposit_paid = True
                project.deposit_payment_id = f"WALLET-{project.id}"
                project.deposit_paid_at = timezone.now()
                project.status = 'deposit_paid'
                project.save()
                messages.success(request, f'Deposit of KSh {project.deposit_amount} paid from wallet!')
                return redirect('projects:detail', project_id=project.id)
            else:
                messages.error(request, 'Insufficient wallet balance.')

    payment_methods = [
        {'id': 'mpesa', 'name': 'M-PESA', 'icon': 'fas fa-mobile-alt'},
        {'id': 'wallet', 'name': 'Wallet Balance', 'icon': 'fas fa-wallet'},
    ]
    context = {
        'project': project,
        'payment_methods': payment_methods,
        'amount': project.deposit_amount,
        'is_deposit': True,
    }
    return render(request, 'payments/process_deposit.html', context)


@login_required
def process_final_payment(request, project_id):
    project = get_object_or_404(Project, id=project_id, customer=request.user)

    if project.final_paid:
        messages.warning(request, 'Final payment already made.')
        return redirect('projects:detail', project_id=project.id)

    if project.status != 'submitted':
        messages.error(request, 'Final payment cannot be processed.')
        return redirect('projects:detail', project_id=project.id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '')

        if payment_method == 'mpesa':
            from .services import MpesaService
            mpesa = MpesaService()
            result = mpesa.stk_push(
                phone_number=phone_number,
                amount=float(project.final_amount),
                account_reference=f"FNL-{project.id}",
                transaction_desc=f"Final payment for {project.title}",
                callback_url=request.build_absolute_uri('/payments/mpesa/callback/')
            )

            if result['success']:
                PaymentTransaction.objects.create(
                    project=project,
                    user=request.user,
                    payment_type='final',
                    payment_method='mpesa',
                    amount=project.final_amount,
                    platform_fee=project.platform_fee,
                    net_amount=project.final_amount - project.platform_fee,
                    checkout_request_id=result['checkout_request_id'],
                    mpesa_phone=phone_number,
                    status='processing',
                    metadata={
                        'checkout_request_id': result['checkout_request_id'],
                        'merchant_request_id': result.get('merchant_request_id'),
                        'mock': result.get('mock', False),
                    }
                )
                messages.info(request, 'M-PESA prompt sent. Enter your PIN.')
                return redirect('payments:mpesa_query', checkout_id=result['checkout_request_id'])
            else:
                messages.error(request, f"M-PESA failed: {result.get('error')}")

        elif payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= project.final_amount:
                wallet.deduct_balance(
                    project.final_amount,
                    transaction_type='payment',
                    description=f'Final for: {project.title}'
                )
                PaymentTransaction.objects.create(
                    project=project, user=request.user,
                    payment_type='final', payment_method='wallet',
                    amount=project.final_amount, platform_fee=project.platform_fee,
                    net_amount=project.final_amount - project.platform_fee,
                    status='completed', completed_at=timezone.now(),
                )
                project.final_paid = True
                project.final_payment_id = f"WALLET-{project.id}"
                project.final_paid_at = timezone.now()
                project.status = 'completed'
                project.completed_at = timezone.now()
                project.save()

                provider = project.provider
                provider.balance += project.provider_payout
                provider.total_earned += project.provider_payout
                provider.completed_projects += 1
                provider.save()

                provider_wallet, _ = Wallet.objects.get_or_create(user=provider)
                provider_wallet.add_balance(
                    project.provider_payout,
                    transaction_type='earning',
                    description=f'Payment for: {project.title}'
                )

                messages.success(request, f'Final payment paid from wallet!')
                return redirect('projects:detail', project_id=project.id)
            else:
                messages.error(request, 'Insufficient wallet balance.')

    context = {
        'project': project,
        'amount': project.final_amount,
        'is_deposit': False,
    }
    return render(request, 'payments/process_final.html', context)


@login_required
def process_refund(request, transaction_id):
    tx = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    if tx.status != 'completed':
        messages.error(request, 'Only completed transactions can be refunded.')
        return redirect('payments:transaction_detail', transaction_id=tx.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        tx.status = 'refunded'
        tx.status_reason = reason
        tx.save()

        if tx.payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.add_balance(
                tx.amount,
                transaction_type='refund',
                description=f'Refund for #{tx.id}: {reason}'
            )
        messages.success(request, 'Refund processed.')
        return redirect('payments:transaction_detail', transaction_id=tx.id)

    return render(request, 'payments/refund.html', {'transaction': tx})


# ============================================================
# PAYMENT METHODS
# ============================================================

@login_required
def payment_methods(request):
    methods = PaymentMethod.objects.filter(user=request.user)
    return render(request, 'payments/methods.html', {'methods': methods})


@login_required
def add_payment_method(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            method = form.save(commit=False)
            method.user = request.user
            method.save()
            messages.success(request, 'Payment method added.')
            return redirect('payments:methods')
    else:
        form = PaymentMethodForm()
    return render(request, 'payments/add_method.html', {'form': form})


@login_required
def remove_payment_method(request, method_id):
    method = get_object_or_404(PaymentMethod, id=method_id, user=request.user)
    if request.method == 'POST':
        method.delete()
        messages.success(request, 'Payment method removed.')
        return redirect('payments:methods')
    return render(request, 'payments/remove_method.html', {'method': method})


# ============================================================
# M-PESA CALLBACKS
# ============================================================

@csrf_exempt
def mpesa_callback(request):
    """
    STK Push callback. Handles both Project and Order payments.
    """
    if request.method != 'POST':
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid method'})

    try:
        data = json.loads(request.body)
        logger.info(f"M-PESA Callback received: {data}")

        stk = data.get('Body', {}).get('stkCallback', {})
        result_code = str(stk.get('ResultCode', ''))
        checkout_id = stk.get('CheckoutRequestID')

        if not checkout_id:
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'No checkout id'})

        tx = PaymentTransaction.objects.filter(
            checkout_request_id=checkout_id
        ).first()

        if not tx:
            logger.warning(f"M-PESA callback: no transaction for {checkout_id}")
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Ignored'})

        if result_code == '0':
            # Extract receipt
            items = stk.get('CallbackMetadata', {}).get('Item', []) or []
            receipt = None
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt = item.get('Value')
                    break

            if tx.mark_completed(receipt=receipt):
                # ---- ORDER deposit ----
                if tx.order_id and tx.payment_type == 'order_deposit':
                    order = tx.order
                    prev = order.status
                    order.deposit_paid = True
                    order.deposit_payment_id = receipt
                    order.deposit_paid_at = timezone.now()
                    order.status = 'deposit_paid'
                    order.save()
                    _log_status(
                        order, tx.user, prev, 'deposit_paid',
                        f'Deposit paid via M-PESA. Receipt: {receipt}'
                    )
                    try:
                        order.provider.provider_profile.flip_phone_public_if_needed()
                    except Exception:
                        pass
                    try:
                        Notification.objects.create(
                            user=order.provider,
                            type='payment',
                            title='Deposit Received',
                            message=(
                                f'KSh {order.deposit_amount:,.0f} deposit received '
                                f'for order #{order.id}.'
                            ),
                            link=f'/projects/orders/{order.id}/',
                        )
                    except Exception:
                        pass

                # ---- LEGACY project deposit ----
                elif tx.project_id and tx.payment_type == 'deposit':
                    project = tx.project
                    project.deposit_paid = True
                    project.deposit_payment_id = receipt
                    project.deposit_paid_at = timezone.now()
                    project.status = 'deposit_paid'
                    project.save()

                # ---- LEGACY project final ----
                elif tx.project_id and tx.payment_type == 'final':
                    project = tx.project
                    project.final_paid = True
                    project.final_payment_id = receipt
                    project.final_paid_at = timezone.now()
                    project.status = 'completed'
                    project.completed_at = timezone.now()
                    project.save()

                    provider = project.provider
                    provider.balance += project.provider_payout
                    provider.total_earned += project.provider_payout
                    provider.completed_projects += 1
                    provider.save()

                    provider_wallet, _ = Wallet.objects.get_or_create(user=provider)
                    provider_wallet.add_balance(
                        project.provider_payout,
                        transaction_type='earning',
                        description=f'Payment for project: {project.title}'
                    )

        else:
            tx.status = 'failed'
            tx.status_reason = (
                stk.get('ResultDesc') or f'ResultCode {result_code}'
            )
            tx.save(update_fields=['status', 'status_reason', 'updated_at'])

        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

    except Exception as e:
        logger.exception(f"M-PESA callback error: {e}")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})


@csrf_exempt
def mpesa_result(request):
    """B2C Result URL (kept for future B2C integration)."""
    if request.method == 'POST':
        logger.info(f"M-PESA B2C Result: {request.body}")
    return JsonResponse({'success': True})


@csrf_exempt
def mpesa_timeout(request):
    """B2C Timeout URL."""
    if request.method == 'POST':
        logger.info(f"M-PESA B2C Timeout: {request.body}")
    return JsonResponse({'success': True})


@login_required
def mpesa_query_status(request, checkout_id):
    """Generic status query endpoint for the legacy flow."""
    from .services import MpesaService
    mpesa = MpesaService()
    result = mpesa.query_status(checkout_id)
    if result['success']:
        return JsonResponse(result)
    return JsonResponse({'error': result.get('error')}, status=400)


# ============================================================
# WALLET (redirects to accounts)
# ============================================================

@login_required
def wallet_dashboard(request):
    return redirect('accounts:wallet')


@login_required
def wallet_deposit(request):
    return redirect('accounts:wallet_deposit')


@login_required
def wallet_withdraw(request):
    return redirect('accounts:wallet_withdraw')


@login_required
def wallet_transactions(request):
    return redirect('accounts:wallet')


# ============================================================
# TRANSACTIONS
# ============================================================

@login_required
def transaction_list(request):
    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).select_related('project', 'order').order_by('-created_at')

    payment_type = request.GET.get('type')
    if payment_type:
        transactions = transactions.filter(payment_type=payment_type)

    status = request.GET.get('status')
    if status:
        transactions = transactions.filter(status=status)

    paginator = Paginator(transactions, 20)
    page = request.GET.get('page')
    try:
        transactions = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        transactions = paginator.page(1)

    context = {
        'transactions': transactions,
        'payment_types': PaymentTransaction.PAYMENT_TYPES,
        'status_choices': PaymentTransaction.STATUS_CHOICES,
    }
    return render(request, 'payments/transactions.html', context)


@login_required
def transaction_detail(request, transaction_id):
    tx = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    return render(request, 'payments/transaction_detail.html', {'transaction': tx})


# ============================================================
# PAYOUTS
# ============================================================

@login_required
def payout_list(request):
    payouts = Payout.objects.filter(user=request.user).order_by('-requested_at')
    return render(request, 'payments/payouts.html', {'payouts': payouts})


@login_required
def request_payout(request):
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            payout.save()

            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.deduct_balance(
                payout.amount,
                transaction_type='withdrawal',
                description=f'Withdrawal request #{payout.id} (processed manually)'
            )
            messages.success(
                request,
                f'Payout of KSh {payout.amount:,.0f} requested. '
                f'Withdrawals are processed within 24 hours.'
            )
            return redirect('payments:payouts')
    else:
        form = PayoutRequestForm()
    return render(request, 'payments/request_payout.html', {'form': form})


@login_required
def payout_detail(request, payout_id):
    payout = get_object_or_404(Payout, id=payout_id, user=request.user)
    return render(request, 'payments/payout_detail.html', {'payout': payout})


# ============================================================
# OTHER WEBHOOKS (unchanged)
# ============================================================

@csrf_exempt
def stripe_webhook(request):
    if request.method == 'POST':
        logger.info(f"Stripe Webhook: {request.body}")
    return JsonResponse({'status': 'success'})


@csrf_exempt
def paypal_webhook(request):
    if request.method == 'POST':
        logger.info(f"PayPal Webhook: {request.body}")
    return JsonResponse({'status': 'success'})