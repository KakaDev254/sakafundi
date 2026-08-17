# payments/services.py
import requests
import base64
import datetime
import json
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class MpesaService:
    """M-PESA Integration using Safaricom Daraja API"""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.base_url = settings.MPESA_BASE_URL
        
        self.access_token = self.get_access_token()
    
    def get_access_token(self):
        """Get OAuth access token from M-PESA"""
        cache_key = 'mpesa_access_token'
        token = cache.get(cache_key)
        
        if token:
            return token
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth}',
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            token = data.get('access_token')
            if token:
                # Cache for 25 minutes (expires in 30)
                cache.set(cache_key, token, 1500)
                return token
        except Exception as e:
            logger.error(f"Failed to get M-PESA token: {str(e)}")
            raise Exception(f"Failed to get M-PESA token: {str(e)}")
        
        return None
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_url):
        """Initiate STK Push (Lipa Na M-PESA Online)"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()
        
        # Format phone number (254XXXXXXXXX)
        if phone_number.startswith('0'):
            phone_number = f"254{phone_number[1:]}"
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:20],
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': data.get('CheckoutRequestID'),
                    'merchant_request_id': data.get('MerchantRequestID'),
                    'response_code': data.get('ResponseCode'),
                    'response_description': data.get('ResponseDescription'),
                    'customer_message': data.get('CustomerMessage'),
                }
            else:
                return {
                    'success': False,
                    'error': data.get('errorMessage') or data.get('ResponseDescription'),
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"M-PESA STK Push error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def query_status(self, checkout_request_id):
        """Query transaction status"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'result_code': data.get('ResultCode'),
                    'result_desc': data.get('ResultDesc'),
                    'mpesa_receipt': data.get('MpesaReceiptNumber'),
                    'amount': data.get('Amount'),
                    'transaction_date': data.get('TransactionDate'),
                }
            else:
                return {
                    'success': False,
                    'error': data.get('errorMessage') or data.get('ResponseDescription'),
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"M-PESA query error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }