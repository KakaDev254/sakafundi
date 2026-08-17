# payments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import json
import logging

from accounts.models import Wallet, WalletTransaction  # Import from accounts
from .models import PaymentMethod, PaymentTransaction, Payout
from .forms import PaymentMethodForm, PayoutRequestForm, WalletDepositForm, WalletWithdrawForm
from projects.models import Project
from notifications.models import Notification

logger = logging.getLogger(__name__)


@login_required
def payment_dashboard(request):
    """Payment dashboard for user"""
    user = request.user
    
    # Get wallet from accounts app
    wallet, created = Wallet.objects.get_or_create(user=user)
    
    # Recent transactions
    transactions = PaymentTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    # Pending payments
    pending_payments = PaymentTransaction.objects.filter(
        user=user,
        status='pending'
    ).count()
    
    # Total spent
    total_spent = PaymentTransaction.objects.filter(
        user=user,
        status='completed',
        payment_type__in=['deposit', 'final']
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Total earnings (for providers)
    total_earnings = 0
    if user.is_provider():
        total_earnings = PaymentTransaction.objects.filter(
            user=user,
            status='completed',
            payment_type='payout'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'pending_payments': pending_payments,
        'total_spent': total_spent,
        'total_earnings': total_earnings,
    }
    return render(request, 'payments/dashboard.html', context)


@login_required
def process_deposit(request, project_id):
    """Process deposit payment for a project"""
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
                transaction = PaymentTransaction.objects.create(
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
                        'merchant_request_id': result.get('merchant_request_id')
                    }
                )
                
                messages.info(request, 'M-PESA STK push sent. Please check your phone and enter your PIN.')
                return redirect('payments:mpesa_query', checkout_id=result['checkout_request_id'])
            else:
                messages.error(request, f'M-PESA payment failed: {result.get("error")}')
        
        elif payment_method == 'wallet':
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= project.deposit_amount:
                wallet.deduct_balance(
                    project.deposit_amount,
                    transaction_type='payment',
                    description=f'Deposit for project: {project.title}'
                )
                
                transaction = PaymentTransaction.objects.create(
                    project=project,
                    user=request.user,
                    payment_type='deposit',
                    payment_method='wallet',
                    amount=project.deposit_amount,
                    platform_fee=0,
                    net_amount=project.deposit_amount,
                    status='completed',
                    completed_at=timezone.now()
                )
                
                project.deposit_paid = True
                project.deposit_payment_id = f"WALLET-{transaction.id}"
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
    """Process final payment for a project"""
    project = get_object_or_404(Project, id=project_id, customer=request.user)
    
    if project.final_paid:
        messages.warning(request, 'Final payment already made.')
        return redirect('projects:detail', project_id=project.id)
    
    if project.status != 'submitted':
        messages.error(request, 'Final payment cannot be processed for this project.')
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
                transaction = PaymentTransaction.objects.create(
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
                        'merchant_request_id': result.get('merchant_request_id')
                    }
                )
                
                messages.info(request, 'M-PESA STK push sent. Please check your phone and enter your PIN.')
                return redirect('payments:mpesa_query', checkout_id=result['checkout_request_id'])
            else:
                messages.error(request, f'M-PESA payment failed: {result.get("error")}')
        
        elif payment_method == 'wallet':
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance >= project.final_amount:
                wallet.deduct_balance(
                    project.final_amount,
                    transaction_type='payment',
                    description=f'Final payment for project: {project.title}'
                )
                
                transaction = PaymentTransaction.objects.create(
                    project=project,
                    user=request.user,
                    payment_type='final',
                    payment_method='wallet',
                    amount=project.final_amount,
                    platform_fee=project.platform_fee,
                    net_amount=project.final_amount - project.platform_fee,
                    status='completed',
                    completed_at=timezone.now()
                )
                
                project.final_paid = True
                project.final_payment_id = f"WALLET-{transaction.id}"
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
                
                # Update provider wallet
                provider_wallet, _ = Wallet.objects.get_or_create(user=provider)
                provider_wallet.add_balance(
                    project.provider_payout,
                    transaction_type='earning',
                    description=f'Payment for project: {project.title}'
                )
                
                messages.success(request, f'Final payment of KSh {project.final_amount} paid from wallet!')
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
        'amount': project.final_amount,
        'platform_fee': project.platform_fee,
        'provider_payout': project.provider_payout,
        'is_deposit': False,
    }
    return render(request, 'payments/process_final.html', context)


@login_required
def process_refund(request, transaction_id):
    """Process a refund for a transaction"""
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    if transaction.status != 'completed':
        messages.error(request, 'Only completed transactions can be refunded.')
        return redirect('payments:transaction_detail', transaction_id=transaction.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        transaction.status = 'refunded'
        transaction.status_reason = reason
        transaction.save()
        
        # Refund to wallet if paid from wallet
        if transaction.payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.add_balance(
                transaction.amount,
                transaction_type='refund',
                description=f'Refund for transaction #{transaction.id}: {reason}'
            )
        
        messages.success(request, 'Refund processed successfully.')
        return redirect('payments:transaction_detail', transaction_id=transaction.id)
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'payments/refund.html', context)


@login_required
def payment_methods(request):
    """Manage payment methods"""
    methods = PaymentMethod.objects.filter(user=request.user)
    
    context = {
        'methods': methods,
    }
    return render(request, 'payments/methods.html', context)


@login_required
def add_payment_method(request):
    """Add a new payment method"""
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            method = form.save(commit=False)
            method.user = request.user
            method.save()
            messages.success(request, 'Payment method added successfully!')
            return redirect('payments:methods')
    else:
        form = PaymentMethodForm()
    
    context = {
        'form': form,
    }
    return render(request, 'payments/add_method.html', context)


@login_required
def remove_payment_method(request, method_id):
    """Remove a payment method"""
    method = get_object_or_404(PaymentMethod, id=method_id, user=request.user)
    
    if request.method == 'POST':
        method.delete()
        messages.success(request, 'Payment method removed.')
        return redirect('payments:methods')
    
    context = {
        'method': method,
    }
    return render(request, 'payments/remove_method.html', context)


@csrf_exempt
def mpesa_callback(request):
    """M-PESA STK Push callback"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"M-PESA Callback: {data}")
            
            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
            
            transaction = PaymentTransaction.objects.filter(
                checkout_request_id=checkout_request_id
            ).first()
            
            if transaction:
                if result_code == '0':
                    mpesa_receipt = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
                    receipt = next((item for item in mpesa_receipt if item.get('Name') == 'MpesaReceiptNumber'), {})
                    
                    transaction.mpesa_receipt = receipt.get('Value')
                    transaction.status = 'completed'
                    transaction.completed_at = timezone.now()
                    transaction.save()
                    
                    if transaction.project:
                        if transaction.payment_type == 'deposit':
                            project = transaction.project
                            project.deposit_paid = True
                            project.deposit_payment_id = transaction.mpesa_receipt
                            project.deposit_paid_at = timezone.now()
                            project.status = 'deposit_paid'
                            project.save()
                            
                            Notification.objects.create(
                                user=project.provider,
                                type='payment',
                                title='Deposit Paid',
                                message=f'Customer paid deposit of KSh {project.deposit_amount}',
                                link=f'/projects/{project.id}/'
                            )
                        
                        elif transaction.payment_type == 'final':
                            project = transaction.project
                            project.final_paid = True
                            project.final_payment_id = transaction.mpesa_receipt
                            project.final_paid_at = timezone.now()
                            project.status = 'completed'
                            project.completed_at = timezone.now()
                            project.save()
                            
                            provider = project.provider
                            provider.balance += project.provider_payout
                            provider.total_earned += project.provider_payout
                            provider.completed_projects += 1
                            provider.save()
                            
                            # Update provider wallet
                            provider_wallet, _ = Wallet.objects.get_or_create(user=provider)
                            provider_wallet.add_balance(
                                project.provider_payout,
                                transaction_type='earning',
                                description=f'Payment for project: {project.title}'
                            )
                            
                            Notification.objects.create(
                                user=project.provider,
                                type='payment',
                                title='Final Payment Received',
                                message=f'Final payment of KSh {project.final_amount} received',
                                link=f'/projects/{project.id}/'
                            )
                else:
                    transaction.status = 'failed'
                    transaction.status_reason = f"Result Code: {result_code}"
                    transaction.save()
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
            
        except Exception as e:
            logger.error(f"M-PESA Callback Error: {str(e)}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request'})


@csrf_exempt
def mpesa_result(request):
    """M-PESA B2C Result URL"""
    if request.method == 'POST':
        logger.info(f"M-PESA Result: {request.body}")
    return JsonResponse({'success': True})


@csrf_exempt
def mpesa_timeout(request):
    """M-PESA Timeout URL"""
    if request.method == 'POST':
        logger.info(f"M-PESA Timeout: {request.body}")
    return JsonResponse({'success': True})


@login_required
def mpesa_query_status(request, checkout_id):
    """Query M-PESA transaction status"""
    from .services import MpesaService
    
    mpesa = MpesaService()
    result = mpesa.query_status(checkout_id)
    
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse({'error': result.get('error')}, status=400)


@login_required
def wallet_dashboard(request):
    """Wallet dashboard - redirect to accounts wallet"""
    return redirect('accounts:wallet')


@login_required
def wallet_deposit(request):
    """Deposit money to wallet - redirect to accounts wallet"""
    return redirect('accounts:wallet_deposit')


@login_required
def wallet_withdraw(request):
    """Withdraw money from wallet - redirect to accounts wallet"""
    return redirect('accounts:wallet_withdraw')


@login_required
def wallet_transactions(request):
    """View wallet transactions - redirect to accounts wallet"""
    return redirect('accounts:wallet')


@login_required
def transaction_list(request):
    """List all transactions"""
    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).select_related('project').order_by('-created_at')
    
    # Filtering
    payment_type = request.GET.get('type')
    if payment_type:
        transactions = transactions.filter(payment_type=payment_type)
    
    status = request.GET.get('status')
    if status:
        transactions = transactions.filter(status=status)
    
    # Pagination
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
    """View transaction details"""
    transaction = get_object_or_404(
        PaymentTransaction, 
        id=transaction_id, 
        user=request.user
    )
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'payments/transaction_detail.html', context)


@login_required
def payout_list(request):
    """List all payouts"""
    payouts = Payout.objects.filter(
        user=request.user
    ).order_by('-requested_at')
    
    context = {
        'payouts': payouts,
    }
    return render(request, 'payments/payouts.html', context)


@login_required
def request_payout(request):
    """Request a payout"""
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            payout.save()
            
            # Deduct from wallet
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.deduct_balance(
                payout.amount,
                transaction_type='withdrawal',
                description=f'Withdrawal request #{payout.id}'
            )
            
            messages.success(request, f'Payout of KSh {payout.amount} requested successfully.')
            return redirect('payments:payouts')
    else:
        form = PayoutRequestForm()
    
    context = {
        'form': form,
    }
    return render(request, 'payments/request_payout.html', context)


@login_required
def payout_detail(request, payout_id):
    """View payout details"""
    payout = get_object_or_404(Payout, id=payout_id, user=request.user)
    
    context = {
        'payout': payout,
    }
    return render(request, 'payments/payout_detail.html', context)


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook endpoint"""
    if request.method == 'POST':
        logger.info(f"Stripe Webhook: {request.body}")
    return JsonResponse({'status': 'success'})


@csrf_exempt
def paypal_webhook(request):
    """PayPal webhook endpoint"""
    if request.method == 'POST':
        logger.info(f"PayPal Webhook: {request.body}")
    return JsonResponse({'status': 'success'})