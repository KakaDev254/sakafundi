# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment dashboard
    path('', views.payment_dashboard, name='dashboard'),
    
    # Payment processing
    path('process-deposit/<int:project_id>/', views.process_deposit, name='process_deposit'),
    path('process-final/<int:project_id>/', views.process_final_payment, name='process_final'),
    path('process-refund/<int:transaction_id>/', views.process_refund, name='process_refund'),
    
    # Payment methods
    path('methods/', views.payment_methods, name='methods'),
    path('add-method/', views.add_payment_method, name='add_method'),
    path('remove-method/<int:method_id>/', views.remove_payment_method, name='remove_method'),
    
    # M-PESA specific
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('mpesa/result/', views.mpesa_result, name='mpesa_result'),
    path('mpesa/timeout/', views.mpesa_timeout, name='mpesa_timeout'),
    path('mpesa/query/<str:checkout_id>/', views.mpesa_query_status, name='mpesa_query'),
    
    # Wallet (redirects to accounts)
    path('wallet/', views.wallet_dashboard, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallet/withdraw/', views.wallet_withdraw, name='wallet_withdraw'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    
    # Transaction history
    path('transactions/', views.transaction_list, name='transactions'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # Payouts
    path('payouts/', views.payout_list, name='payouts'),
    path('payouts/request/', views.request_payout, name='request_payout'),
    path('payouts/<int:payout_id>/', views.payout_detail, name='payout_detail'),
    
    # Webhooks
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('webhook/paypal/', views.paypal_webhook, name='paypal_webhook'),
]