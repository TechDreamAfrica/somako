from accounts.notification_service import send_notification


def notify_pharmacy_order_placed(order):
    """Notify pharmacy owner when new order is placed"""
    if order.pharmacy and order.pharmacy.owner:
        send_notification(
            user=order.pharmacy.owner,
            notification_type='pharmacy_order_placed',
            title='New Pharmacy Order!',
            message=f'New medicine order #{order.order_number} received. Total: ${order.total_amount}. Customer: {order.customer.get_full_name() or order.customer.username}',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(order.id),
            reference_type='PharmacyOrder',
            data={
                'order_number': order.order_number,
                'total': str(order.total_amount),
                'items_count': order.items.count()
            }
        )


def notify_pharmacy_order_confirmed(order):
    """Notify customer when order is confirmed"""
    send_notification(
        user=order.customer,
        notification_type='pharmacy_order_confirmed',
        title='Pharmacy Order Confirmed!',
        message=f'Your medicine order #{order.order_number} has been confirmed. Total: ${order.total_amount}. We\'re preparing your order.',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='PharmacyOrder',
        data={
            'order_number': order.order_number,
            'total': str(order.total_amount)
        }
    )


def notify_pharmacy_order_ready(order):
    """Notify customer when order is ready for pickup"""
    send_notification(
        user=order.customer,
        notification_type='pharmacy_order_ready',
        title='Medicine Ready for Pickup!',
        message=f'Your medicine order #{order.order_number} is ready for pickup at {order.pharmacy.name if order.pharmacy else "the pharmacy"}.',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='PharmacyOrder'
    )


def notify_pharmacy_order_delivered(order):
    """Notify customer when order is delivered"""
    send_notification(
        user=order.customer,
        notification_type='pharmacy_order_delivered',
        title='Medicine Delivered!',
        message=f'Your medicine order #{order.order_number} has been delivered. Please follow the prescribed dosage. Stay healthy!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='PharmacyOrder'
    )
