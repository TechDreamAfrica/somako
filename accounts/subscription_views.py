from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from datetime import timedelta
import uuid

from .subscription_models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from payment.models import Payment
from payment.paystack import PaystackAPI


def provider_required(view_func):
    """Decorator to ensure only providers can access subscription features"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue.')
            return redirect('accounts:login')

        # Check if user has a provider role (not general user)
        user = request.user
        provider_roles = ['seller', 'pharmacy_owner', 'restaurant_owner', 'landlord', 'equipment_owner', 'driver']
        is_provider = any(user.has_role(role) for role in provider_roles)

        if not is_provider:
            messages.error(request, 'Subscriptions are only available to service providers.')
            return redirect('accounts:dashboard')

        return view_func(request, *args, **kwargs)
    return wrapper


def subscription_plans(request):
    """Display all available subscription plans with optional service filtering"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')

    # Check if user is a provider based on role
    is_provider = False
    user_subscription = None
    service_name = request.GET.get('service', '')

    if request.user.is_authenticated:
        provider_roles = ['seller', 'pharmacy_owner', 'restaurant_owner', 'landlord', 'equipment_owner', 'driver']
        is_provider = any(request.user.has_role(role) for role in provider_roles)

        if is_provider:
            try:
                user_subscription = UserSubscription.objects.get(user=request.user)
            except UserSubscription.DoesNotExist:
                pass
    
    # Service-specific context
    service_contexts = {
        'driver': {
            'icon': 'fa-car',
            'color': '#8b5cf6',
            'heading': 'Driver Subscription Plans',
            'subheading': 'Choose a plan to start accepting rides and earning',
        },
        'restaurant_owner': {
            'icon': 'fa-utensils',
            'color': '#ea580c',
            'heading': 'Restaurant Owner Plans',
            'subheading': 'Grow your food delivery business with premium features',
        },
        'pharmacy_owner': {
            'icon': 'fa-pills',
            'color': '#dc2626',
            'heading': 'Pharmacy Owner Plans',
            'subheading': 'Expand your pharmacy reach with our platform',
        },
        'seller': {
            'icon': 'fa-shopping-bag',
            'color': '#3b82f6',
            'heading': 'Shop Seller Plans',
            'subheading': 'Boost your online store with advanced tools',
        },
        'landlord': {
            'icon': 'fa-home',
            'color': '#059669',
            'heading': 'Landlord Plans',
            'subheading': 'List more properties and reach more tenants',
        },
    }
    
    service_context = service_contexts.get(service_name, {
        'icon': 'fa-crown',
        'color': '#6366f1',
        'heading': 'Provider Subscription Plans',
        'subheading': 'Select the right plan for your business needs',
    })

    context = {
        'plans': plans,
        'user_subscription': user_subscription,
        'is_provider': is_provider,
        'service_name': service_name,
        'service_context': service_context,
    }
    return render(request, 'accounts/subscription_plans.html', context)


@provider_required
def subscribe(request, plan_id):
    """Initiate subscription payment"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

    if request.method == 'POST':
        # Generate unique payment reference
        payment_reference = f"SUB-{uuid.uuid4().hex[:12].upper()}"

        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=plan.price,
            currency='GHS',
            payment_method='paystack',
            status='pending',
            source_app='subscription',
            order_id=str(plan.id),
            paystack_reference=payment_reference,
            customer_email=request.user.email,
            customer_phone=getattr(request.user, 'phone', ''),
            description=f'Subscription to {plan.display_name} plan',
            metadata={
                'plan_id': plan.id,
                'plan_name': plan.display_name,
                'user_id': request.user.id,
                'username': request.user.username,
            }
        )

        # Initialize Paystack transaction
        paystack = PaystackAPI()
        callback_url = request.build_absolute_uri(reverse('accounts:subscription_verify', args=[payment_reference]))

        result = paystack.initialize_transaction(
            email=request.user.email,
            amount=plan.price,
            reference=payment_reference,
            callback_url=callback_url,
            metadata=payment.metadata
        )

        if result['status']:
            # Update payment with Paystack details
            payment.paystack_access_code = result['data'].get('access_code')
            payment.paystack_authorization_url = result['data'].get('authorization_url')
            payment.save()

            # Redirect to Paystack payment page
            return redirect(result['data'].get('authorization_url'))
        else:
            messages.error(request, f'Payment initialization failed: {result["message"]}')
            payment.delete()
            return redirect('accounts:subscription_plans')

    context = {
        'plan': plan,
    }
    return render(request, 'accounts/subscribe_confirm.html', context)


@provider_required
def subscription_verify(request, reference):
    """Verify subscription payment and activate subscription"""
    # Get payment record
    try:
        payment = Payment.objects.get(paystack_reference=reference)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('accounts:subscription_plans')

    # Verify with Paystack
    paystack = PaystackAPI()
    result = paystack.verify_transaction(reference)

    if result['status'] and result['data'].get('status') == 'success':
        # Mark payment as successful
        payment.mark_as_paid()
        payment.transaction_id = result['data'].get('id')
        payment.gateway_response = str(result['data'])
        payment.save()

        # Get plan from metadata
        plan_id = payment.metadata.get('plan_id')
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        # Create or update subscription
        try:
            user_sub = UserSubscription.objects.get(user=request.user)
            old_plan = user_sub.plan

            # Update existing subscription
            user_sub.plan = plan
            user_sub.start_date = timezone.now()
            user_sub.end_date = timezone.now() + timedelta(days=30)
            user_sub.next_billing_date = user_sub.end_date
            user_sub.status = 'active'
            user_sub.last_payment_date = timezone.now()
            user_sub.last_payment_amount = plan.price
            user_sub.auto_renew = True
            user_sub.save()

            # Determine action type
            if old_plan and old_plan.price < plan.price:
                action = 'upgraded'
            elif old_plan and old_plan.price > plan.price:
                action = 'downgraded'
            else:
                action = 'renewed'

        except UserSubscription.DoesNotExist:
            # Create new subscription
            user_sub = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=30),
                next_billing_date=timezone.now() + timedelta(days=30),
                status='active',
                last_payment_date=timezone.now(),
                last_payment_amount=plan.price,
            )
            action = 'subscribed'

        # Create history record
        SubscriptionHistory.objects.create(
            user=request.user,
            plan=plan,
            action=action,
            amount=plan.price,
            notes=f"Payment successful - Reference: {reference}"
        )
        
        # Send subscription notification
        try:
            from .notification_service import send_notification
            notification_title = f'Subscription {action.title()}!'
            notification_message = f'Your {plan.display_name} subscription is now active. Enjoy all the premium features until {user_sub.end_date.strftime("%B %d, %Y")}.'
            send_notification(
                user=request.user,
                notification_type='subscription_created' if action == 'subscribed' else 'subscription_renewed',
                title=notification_title,
                message=notification_message,
                channels=['in_app', 'email'],
                reference_id=str(user_sub.id),
                reference_type='UserSubscription'
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send subscription notification: {e}")

        messages.success(request, f'Payment successful! You are now subscribed to {plan.display_name} plan.')
        return redirect('accounts:subscription_manage')
    else:
        # Payment failed
        payment.mark_as_failed(result.get('message'))
        messages.error(request, f'Payment verification failed: {result.get("message")}')
        return redirect('accounts:subscription_plans')


@provider_required
def subscription_manage(request):
    """Manage user's subscription"""
    try:
        user_sub = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        messages.info(request, 'You don\'t have an active subscription. Choose a plan to get started!')
        return redirect('accounts:subscription_plans')

    # Get subscription history
    history = SubscriptionHistory.objects.filter(user=request.user)[:10]

    # Get recent payments
    payments = Payment.objects.filter(
        user=request.user,
        source_app='subscription'
    )[:5]

    context = {
        'subscription': user_sub,
        'history': history,
        'payments': payments,
    }
    return render(request, 'accounts/subscription_manage.html', context)


@provider_required
def subscription_cancel(request):
    """Cancel user's subscription"""
    try:
        user_sub = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        messages.error(request, 'No subscription found.')
        return redirect('accounts:subscription_plans')

    if request.method == 'POST':
        user_sub.cancel()

        # Create history record
        SubscriptionHistory.objects.create(
            user=request.user,
            plan=user_sub.plan,
            action='cancelled',
            notes='User cancelled subscription'
        )

        messages.success(request, 'Your subscription has been cancelled. You can still use it until the end of the billing period.')
        return redirect('accounts:subscription_manage')

    context = {
        'subscription': user_sub,
    }
    return render(request, 'accounts/subscription_cancel.html', context)


@provider_required
def subscription_renew(request):
    """Manually renew subscription"""
    try:
        user_sub = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        messages.error(request, 'No subscription found.')
        return redirect('accounts:subscription_plans')

    if request.method == 'POST':
        # Redirect to payment for renewal
        return redirect('accounts:subscribe', plan_id=user_sub.plan.id)

    context = {
        'subscription': user_sub,
    }
    return render(request, 'accounts/subscription_renew.html', context)


@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook events"""
    if request.method == 'POST':
        # Get signature from header
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')

        # Verify signature
        paystack = PaystackAPI()
        if not paystack.verify_webhook_signature(request.body, signature):
            return HttpResponse('Invalid signature', status=400)

        import json
        event_data = json.loads(request.body)
        event_type = event_data.get('event')

        # Log webhook
        from payment.models import PaystackWebhookLog
        PaystackWebhookLog.objects.create(
            event_type=event_type,
            event_data=event_data,
        )

        # Handle charge.success event
        if event_type == 'charge.success':
            data = event_data.get('data', {})
            reference = data.get('reference')

            try:
                payment = Payment.objects.get(paystack_reference=reference)
                if payment.status == 'pending':
                    # Process payment similar to verify view
                    payment.mark_as_paid()
                    payment.transaction_id = data.get('id')
                    payment.gateway_response = str(data)
                    payment.save()

                    # Update subscription if needed
                    if payment.source_app == 'subscription':
                        plan_id = payment.metadata.get('plan_id')
                        if plan_id:
                            plan = SubscriptionPlan.objects.get(id=plan_id)
                            user = payment.user

                            try:
                                user_sub = UserSubscription.objects.get(user=user)
                                user_sub.renew()
                                action = 'renewed'
                            except UserSubscription.DoesNotExist:
                                user_sub = UserSubscription.objects.create(
                                    user=user,
                                    plan=plan,
                                    start_date=timezone.now(),
                                    end_date=timezone.now() + timedelta(days=30),
                                    next_billing_date=timezone.now() + timedelta(days=30),
                                    status='active',
                                    last_payment_date=timezone.now(),
                                    last_payment_amount=plan.price,
                                )
                                action = 'subscribed'
                            
                            # Create subscription history record
                            SubscriptionHistory.objects.create(
                                user=user,
                                plan=plan,
                                action=action,
                                amount=plan.price,
                                notes=f"Webhook payment successful - Reference: {reference}"
                            )
            except Payment.DoesNotExist:
                pass

        return HttpResponse('OK', status=200)

    return HttpResponse('Method not allowed', status=405)
