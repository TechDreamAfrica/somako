"""
Payment Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
import logging

from .models import Payment, PaystackWebhookLog
from .paystack import PaystackAPI

logger = logging.getLogger(__name__)


@login_required
def initiate_payment(request):
    """
    Initiate a payment transaction

    Expected POST data:
    - amount: Payment amount
    - source_app: Source app (rent, food, shop, pharmacy, ride)
    - order_id: Order ID from source app
    - description: Payment description
    - payment_method: Payment method (cash, card, mobile_money, paystack)
    """
    if request.method == 'POST':
        try:
            amount = request.POST.get('amount')
            source_app = request.POST.get('source_app')
            order_id = request.POST.get('order_id')
            description = request.POST.get('description', '')
            payment_method = request.POST.get('payment_method', 'paystack')

            # Validation
            if not all([amount, source_app, order_id]):
                messages.error(request, 'Missing required payment information')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            # Convert amount to float and validate
            try:
                amount_float = float(amount)
                if amount_float <= 0:
                    raise ValueError("Amount must be greater than zero")
            except (ValueError, TypeError) as e:
                messages.error(request, f'Invalid amount: {amount}')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            # Handle cash payment
            if payment_method in ['cash', 'cash_on_delivery']:
                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount_float,
                    payment_method='cash',
                    status='pending',
                    source_app=source_app,
                    order_id=order_id,
                    customer_email=request.user.email,
                    customer_phone=getattr(request.user, 'phone_number', ''),
                    description=description,
                )
                messages.success(request, 'Order placed! Please prepare cash for delivery.')
                return redirect('payment:payment_success', payment_id=payment.payment_id)

            # Determine payment channels based on payment method
            channels = None
            if payment_method == 'card':
                channels = ['card']
            elif payment_method == 'mobile_money':
                channels = ['mobile_money']
            elif payment_method == 'bank':
                channels = ['bank', 'ussd']
            else:
                # Default paystack - enable all channels
                channels = ['card', 'mobile_money', 'bank', 'ussd']

            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                amount=amount_float,
                payment_method=payment_method if payment_method in ['card', 'mobile_money'] else 'paystack',
                status='pending',
                source_app=source_app,
                order_id=order_id,
                customer_email=request.user.email,
                customer_phone=getattr(request.user, 'phone_number', ''),
                description=description,
                paystack_reference=str(uuid.uuid4()),
            )

            # Build callback URL with payment ID
            callback_url = request.build_absolute_uri(
                f"/payment/callback/?payment_id={payment.payment_id}"
            )

            # Initialize Paystack transaction
            paystack = PaystackAPI()
            result = paystack.initialize_transaction(
                email=request.user.email,
                amount=amount_float,
                reference=payment.paystack_reference,
                callback_url=callback_url,
                channels=channels,
                metadata={
                    'payment_id': str(payment.payment_id),
                    'source_app': source_app,
                    'order_id': order_id,
                    'user_id': request.user.id,
                    'payment_method': payment_method,
                    'custom_fields': [
                        {
                            'display_name': 'Order Number',
                            'variable_name': 'order_number',
                            'value': order_id
                        },
                        {
                            'display_name': 'Customer Name',
                            'variable_name': 'customer_name',
                            'value': request.user.get_full_name() or request.user.username
                        }
                    ]
                }
            )

            if result['status']:
                data = result['data']
                payment.paystack_access_code = data.get('access_code')
                payment.paystack_authorization_url = data.get('authorization_url')
                payment.status = 'processing'
                payment.save()

                logger.info(f"Payment initialized: {payment.payment_id} - {amount_float} GHS - Channels: {channels}")

                # Redirect to Paystack payment page
                return redirect(data.get('authorization_url'))
            else:
                error_msg = result.get('message', 'Unknown error')
                payment.mark_as_failed(error_msg)
                logger.error(f"Payment initialization failed: {error_msg}")
                messages.error(request, f"Payment initialization failed: {error_msg}")
                return redirect(request.META.get('HTTP_REFERER', '/'))
                return redirect(request.META.get('HTTP_REFERER', '/'))

        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            messages.error(request, 'An error occurred while processing your payment')
            return redirect(request.META.get('HTTP_REFERER', '/'))

    return render(request, 'payment/initiate.html')


@login_required
def payment_callback(request):
    """
    Handle callback from Paystack after payment
    """
    reference = request.GET.get('reference')
    payment_id = request.GET.get('payment_id')

    if not reference:
        messages.error(request, 'Invalid payment reference')
        return redirect('accounts:dashboard')

    try:
        # Try to get payment by reference or payment_id
        if reference:
            payment = Payment.objects.get(paystack_reference=reference)
        elif payment_id:
            payment = Payment.objects.get(payment_id=payment_id)
        else:
            raise Payment.DoesNotExist

        # Verify transaction with Paystack
        paystack = PaystackAPI()
        result = paystack.verify_transaction(reference)

        if result['status']:
            data = result['data']
            payment_status = data.get('status')
            
            logger.info(f"Payment callback - Reference: {reference}, Status: {payment_status}")
            
            if payment_status == 'success':
                payment.mark_as_paid()
                payment.transaction_id = data.get('id')
                payment.gateway_response = json.dumps(data)
                
                # Extract payment channel info
                channel = data.get('channel')
                if channel:
                    payment.metadata['payment_channel'] = channel
                
                payment.save()

                # Send notifications based on source app
                try:
                    if payment.source_app == 'food':
                        from utils.sms_utils import send_order_notification, send_customer_order_confirmation
                        from food.models import Order
                        
                        order = Order.objects.filter(order_number=payment.order_id).first()
                        if order:
                            send_order_notification(order, status_change=False)
                            send_customer_order_confirmation(order)
                except Exception as e:
                    logger.error(f"Failed to send payment confirmation notifications: {e}")

                messages.success(request, 'Payment successful! Thank you for your order.')
                return redirect('payment:payment_success', payment_id=payment.payment_id)
            
            elif payment_status == 'failed':
                payment.mark_as_failed(data.get('gateway_response', 'Payment declined'))
                messages.error(request, f"Payment failed: {data.get('gateway_response', 'Payment was declined')}")
                return redirect('payment:payment_failed', payment_id=payment.payment_id)
            
            else:
                # Handle other statuses (pending, abandoned, etc.)
                payment.status = payment_status
                payment.gateway_response = json.dumps(data)
                payment.save()
                messages.warning(request, f'Payment status: {payment_status}. Please contact support if this persists.')
                return redirect('accounts:dashboard')
        else:
            payment.mark_as_failed(result.get('message'))
            messages.error(request, 'Payment verification failed')
            return redirect('payment:payment_failed', payment_id=payment.payment_id)

    except Payment.DoesNotExist:
        logger.error(f"Payment not found - Reference: {reference}, Payment ID: {payment_id}")
        messages.error(request, 'Payment record not found')
        return redirect('accounts:dashboard')
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while verifying your payment')
        return redirect('accounts:dashboard')


@login_required
def payment_success(request, payment_id):
    """Display payment success page"""
    payment = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    return render(request, 'payment/success.html', {'payment': payment})


@login_required
def payment_failed(request, payment_id):
    """Display payment failed page"""
    payment = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    return render(request, 'payment/failed.html', {'payment': payment})


@login_required
def payment_history(request):
    """Display user's payment history"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payment/history.html', {'payments': payments})


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """
    Handle webhook events from Paystack
    """
    try:
        # Get the signature
        signature = request.headers.get('X-Paystack-Signature')
        payload = request.body

        # Verify signature
        paystack = PaystackAPI()
        if not paystack.verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            return HttpResponse(status=400)

        # Parse event data
        event_data = json.loads(payload)
        event_type = event_data.get('event')

        # Log webhook event
        webhook_log = PaystackWebhookLog.objects.create(
            event_type=event_type,
            event_data=event_data
        )

        # Handle charge.success event
        if event_type == 'charge.success':
            data = event_data.get('data', {})
            reference = data.get('reference')

            try:
                payment = Payment.objects.get(paystack_reference=reference)
                if payment.status != 'success':
                    payment.mark_as_paid()
                    payment.transaction_id = data.get('id')
                    payment.gateway_response = json.dumps(data)
                    payment.save()

                    webhook_log.payment = payment
                    webhook_log.processed = True
                    webhook_log.save()

                    logger.info(f"Webhook processed successfully for payment: {reference}")
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for reference: {reference}")

        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return HttpResponse(status=500)


@login_required
def verify_payment(request, reference):
    """
    Verify a payment manually using reference
    """
    try:
        payment = Payment.objects.get(paystack_reference=reference, user=request.user)

        paystack = PaystackAPI()
        result = paystack.verify_transaction(reference)

        if result['status']:
            data = result['data']
            return JsonResponse({
                'status': True,
                'payment_status': data.get('status'),
                'amount': data.get('amount'),
                'paid_at': data.get('paid_at'),
            })
        else:
            return JsonResponse({
                'status': False,
                'message': result.get('message')
            })

    except Payment.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Payment not found'
        }, status=404)
