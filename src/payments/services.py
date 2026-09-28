# payments/services.py
import requests
import base64
import datetime
import uuid
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class MpesaService:
    """
    M-PESA Integration using Safaricom Daraja API.

    Supports:
    - STK Push (Lipa Na M-PESA Online) for collections — works with
      Business One Account, Paybill, and Till.
    - STK Query for polling payment status.

    Note: this version does NOT call B2C. Provider payouts flow to
    their SakaFundi wallet, and physical withdrawals are handled via
    a separate (Phase 4) process.
    """

    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.base_url = settings.MPESA_BASE_URL
        self.mock = getattr(settings, 'MPESA_MOCK', False)

        # Only fetch token in live mode
        self.access_token = None
        if not self.mock:
            self.access_token = self.get_access_token()

    # --------------------------------------------------------
    # OAuth
    # --------------------------------------------------------
    def get_access_token(self):
        """Get OAuth access token from M-PESA. Cached for 25 minutes."""
        cache_key = 'mpesa_access_token'
        token = cache.get(cache_key)
        if token:
            return token

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        headers = {'Authorization': f'Basic {auth}'}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            token = data.get('access_token')
            if token:
                cache.set(cache_key, token, 1500)
                return token
        except Exception as e:
            logger.error(f"Failed to get M-PESA token: {e}")
            raise Exception(f"Failed to get M-PESA token: {e}")

        return None

    # --------------------------------------------------------
    # Phone normalisation
    # --------------------------------------------------------
    @staticmethod
    def _normalize_phone(phone):
        """Return phone as 254XXXXXXXXX."""
        phone = ''.join(filter(str.isdigit, phone))
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('254'):
            pass
        elif len(phone) == 9:
            phone = '254' + phone
        return phone

    # --------------------------------------------------------
    # STK Push
    # --------------------------------------------------------
    def stk_push(self, phone_number, amount, account_reference,
                 transaction_desc, callback_url, transaction_type=None):
        """
        Initiate STK Push. Handles both mock mode and real Daraja.

        transaction_type: 'CustomerPayBillOnline' (default) or
                          'CustomerBuyGoodsOnline' for Till numbers.
        """
        phone_number = self._normalize_phone(phone_number)

        # ---- Mock mode ----
        if self.mock:
            fake_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            logger.info(
                f"[MPESA MOCK] STK Push: phone={phone_number} "
                f"amount={amount} ref={account_reference} "
                f"checkout_id={fake_id}"
            )
            return {
                'success': True,
                'checkout_request_id': fake_id,
                'merchant_request_id': f"MOCK-{fake_id}",
                'response_code': '0',
                'response_description': 'Mock accepted',
                'customer_message': 'Mock: please enter your PIN on your phone.',
                'mock': True,
            }

        # ---- Real API ----
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": transaction_type or "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": (account_reference or '')[:12],
            "TransactionDesc": (transaction_desc or '')[:20],
        }

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
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
            return {
                'success': False,
                'error': data.get('errorMessage') or data.get('ResponseDescription'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"M-PESA STK Push error: {e}")
            return {'success': False, 'error': str(e)}

    # --------------------------------------------------------
    # STK Query
    # --------------------------------------------------------
    def query_status(self, checkout_request_id):
        """
        Query STK Push status. In mock mode, simulates success after
        a few seconds so the frontend polling exercises the same path.
        """
        # ---- Mock mode ----
        if self.mock:
            # Consider it successful immediately (frontend polls anyway)
            return {
                'success': True,
                'result_code': '0',
                'result_desc': 'Mock: payment successful',
                'mpesa_receipt': f"MOCKR{uuid.uuid4().hex[:8].upper()}",
                'amount': 0,
                'transaction_date': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                'mock': True,
            }

        # ---- Real API ----
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
            response = requests.post(url, json=payload, headers=headers, timeout=15)
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
            return {
                'success': False,
                'error': data.get('errorMessage') or data.get('ResponseDescription'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"M-PESA query error: {e}")
            return {'success': False, 'error': str(e)}