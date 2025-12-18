"""
Paystack API Integration Service
"""
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PaystackAPI:
    """Handle all Paystack API interactions"""

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initialize_transaction(self, email, amount, reference, callback_url=None, metadata=None, channels=None):
        """
        Initialize a payment transaction

        Args:
            email: Customer's email
            amount: Amount in kobo (multiply by 100 for cedis to pesewas)
            reference: Unique transaction reference
            callback_url: URL to redirect after payment
            metadata: Additional data to attach to transaction
            channels: List of payment channels (e.g., ['card', 'mobile_money', 'bank'])

        Returns:
            dict: Response from Paystack API
        """
        url = f'{self.base_url}/transaction/initialize'

        # Convert amount to pesewas (multiply by 100)
        amount_in_pesewas = int(float(amount) * 100)

        payload = {
            'email': email,
            'amount': amount_in_pesewas,
            'reference': reference,
            'currency': 'GHS',
        }

        if callback_url:
            payload['callback_url'] = callback_url
        else:
            payload['callback_url'] = settings.PAYSTACK_CALLBACK_URL

        if metadata:
            payload['metadata'] = metadata

        # Add payment channels (enables card, mobile money, etc.)
        if channels:
            payload['channels'] = channels
        else:
            # Default: Enable all payment methods
            payload['channels'] = ['card', 'mobile_money', 'bank', 'ussd']

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Paystack transaction initialized: {reference} - Channels: {payload.get('channels')}")
            return {
                'status': True,
                'data': result.get('data', {}),
                'message': result.get('message', 'Transaction initialized')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack initialization error: {str(e)}")
            error_message = str(e)
            try:
                # Try to extract more detailed error from response
                if hasattr(e, 'response') and e.response is not None:
                    error_data = e.response.json()
                    error_message = error_data.get('message', error_message)
            except:
                pass
            return {
                'status': False,
                'message': f'Error initializing transaction: {error_message}'
            }

    def verify_transaction(self, reference):
        """
        Verify a transaction using its reference

        Args:
            reference: Transaction reference

        Returns:
            dict: Transaction status and details
        """
        url = f'{self.base_url}/transaction/verify/{reference}'

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()

            if result.get('status'):
                data = result.get('data', {})
                logger.info(f"Transaction verified: {reference} - Status: {data.get('status')}")
                return {
                    'status': True,
                    'data': data,
                    'message': result.get('message', 'Verification successful')
                }
            else:
                logger.warning(f"Transaction verification failed: {reference}")
                return {
                    'status': False,
                    'message': result.get('message', 'Verification failed')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'status': False,
                'message': f'Error verifying transaction: {str(e)}'
            }

    def list_transactions(self, page=1, per_page=50):
        """
        List transactions

        Args:
            page: Page number
            per_page: Number of transactions per page

        Returns:
            dict: List of transactions
        """
        url = f'{self.base_url}/transaction'
        params = {
            'page': page,
            'perPage': per_page
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()

            return {
                'status': True,
                'data': result.get('data', []),
                'message': result.get('message', 'Transactions retrieved')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack list transactions error: {str(e)}")
            return {
                'status': False,
                'message': f'Error fetching transactions: {str(e)}'
            }

    def verify_webhook_signature(self, payload, signature):
        """
        Verify webhook signature from Paystack

        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header value

        Returns:
            bool: True if signature is valid
        """
        import hmac
        import hashlib

        if not settings.PAYSTACK_WEBHOOK_SECRET:
            logger.warning("PAYSTACK_WEBHOOK_SECRET not configured")
            return False

        computed_signature = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        return computed_signature == signature
