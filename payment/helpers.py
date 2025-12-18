"""
Payment Helper Functions
"""
from .models import Payment
from .paystack import PaystackAPI
import uuid
import logging

logger = logging.getLogger(__name__)


def create_payment(user, amount, source_app, order_id, description='', payment_method='paystack'):
    """
    Create a payment record for any app

    Args:
        user: User making the payment
        amount: Payment amount (Decimal)
        source_app: Source app ('food', 'shop', 'pharmacy', 'rent', 'ride')
        order_id: Order/Booking ID from source app
        description: Payment description
        payment_method: Payment method ('paystack', 'cash', 'mobile_money')

    Returns:
        Payment object
    """
    payment = Payment.objects.create(
        user=user,
        amount=amount,
        payment_method=payment_method,
        status='pending' if payment_method == 'cash' else 'processing',
        source_app=source_app,
        order_id=order_id,
        customer_email=user.email,
        customer_phone=getattr(user, 'phone_number', ''),
        description=description,
        paystack_reference=str(uuid.uuid4()) if payment_method == 'paystack' else None,
    )
    return payment


def initialize_paystack_payment(payment):
    """
    Initialize Paystack payment for a payment record

    Args:
        payment: Payment object

    Returns:
        dict: {'status': bool, 'authorization_url': str, 'message': str}
    """
    if payment.payment_method != 'paystack':
        return {
            'status': False,
            'message': 'Payment method is not Paystack'
        }

    paystack = PaystackAPI()
    result = paystack.initialize_transaction(
        email=payment.customer_email,
        amount=payment.amount,
        reference=payment.paystack_reference,
        metadata={
            'payment_id': str(payment.payment_id),
            'source_app': payment.source_app,
            'order_id': payment.order_id,
            'user_id': payment.user.id,
        }
    )

    if result['status']:
        data = result['data']
        payment.paystack_access_code = data.get('access_code')
        payment.paystack_authorization_url = data.get('authorization_url')
        payment.status = 'processing'
        payment.save()

        return {
            'status': True,
            'authorization_url': data.get('authorization_url'),
            'access_code': data.get('access_code'),
            'message': 'Payment initialized successfully'
        }
    else:
        payment.mark_as_failed(result.get('message'))
        return {
            'status': False,
            'message': result.get('message', 'Payment initialization failed')
        }


def verify_paystack_payment(payment):
    """
    Verify Paystack payment

    Args:
        payment: Payment object

    Returns:
        dict: {'status': bool, 'message': str, 'data': dict}
    """
    if not payment.paystack_reference:
        return {
            'status': False,
            'message': 'No Paystack reference found'
        }

    paystack = PaystackAPI()
    result = paystack.verify_transaction(payment.paystack_reference)

    if result['status']:
        data = result['data']
        if data.get('status') == 'success':
            payment.mark_as_paid()
            payment.transaction_id = data.get('id')
            payment.gateway_response = str(data)
            payment.save()

            return {
                'status': True,
                'message': 'Payment verified successfully',
                'data': data
            }
        else:
            payment.mark_as_failed(data.get('gateway_response'))
            return {
                'status': False,
                'message': f"Payment failed: {data.get('gateway_response', 'Unknown error')}",
                'data': data
            }
    else:
        payment.mark_as_failed(result.get('message'))
        return {
            'status': False,
            'message': result.get('message', 'Payment verification failed')
        }
