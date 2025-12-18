from accounts.notification_service import send_notification


def notify_shop_order_placed(order):
    """Notify seller when new order is placed"""
    if order.seller:
        send_notification(
            user=order.seller,
            notification_type='shop_order_placed',
            title='New Shop Order!',
            message=f'New order #{order.order_number} received. Total: ${order.total_amount}. Customer: {order.customer.get_full_name() or order.customer.username}',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(order.id),
            reference_type='ShopOrder',
            data={
                'order_number': order.order_number,
                'total': str(order.total_amount),
                'items_count': order.items.count()
            }
        )


def notify_shop_order_confirmed(order):
    """Notify customer when order is confirmed"""
    send_notification(
        user=order.customer,
        notification_type='shop_order_confirmed',
        title='Order Confirmed!',
        message=f'Your order #{order.order_number} has been confirmed. Total: ${order.total_amount}. We\'ll notify you when it ships.',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='ShopOrder',
        data={
            'order_number': order.order_number,
            'total': str(order.total_amount)
        }
    )


def notify_shop_order_shipped(order):
    """Notify customer when order is shipped"""
    tracking_info = f' Tracking: {order.tracking_number}' if hasattr(order, 'tracking_number') and order.tracking_number else ''

    send_notification(
        user=order.customer,
        notification_type='shop_order_shipped',
        title='Order Shipped!',
        message=f'Your order #{order.order_number} has been shipped!{tracking_info}',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='ShopOrder',
        data={
            'order_number': order.order_number,
            'tracking_number': getattr(order, 'tracking_number', '')
        }
    )


def notify_shop_order_delivered(order):
    """Notify customer when order is delivered"""
    send_notification(
        user=order.customer,
        notification_type='shop_order_delivered',
        title='Order Delivered!',
        message=f'Your order #{order.order_number} has been delivered. Thank you for shopping with Soma Ko!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='ShopOrder'
    )
