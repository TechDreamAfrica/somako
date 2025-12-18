from accounts.notification_service import send_notification


def notify_food_order_placed(order):
    """Notify restaurant owner when new order is placed"""
    if order.restaurant and order.restaurant.owner:
        send_notification(
            user=order.restaurant.owner,
            notification_type='food_order_placed',
            title='New Food Order!',
            message=f'New order #{order.order_number} received. Total: ${order.total_amount}. Customer: {order.customer.get_full_name() or order.customer.username}',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(order.id),
            reference_type='FoodOrder',
            data={
                'order_number': order.order_number,
                'total': str(order.total_amount),
                'customer': order.customer.get_full_name() or order.customer.username
            }
        )


def notify_food_order_confirmed(order):
    """Notify customer when order is confirmed"""
    send_notification(
        user=order.customer,
        notification_type='food_order_confirmed',
        title='Order Confirmed!',
        message=f'Your order #{order.order_number} from {order.restaurant.name} has been confirmed. Total: ${order.total_amount}',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='FoodOrder',
        data={
            'order_number': order.order_number,
            'restaurant': order.restaurant.name,
            'total': str(order.total_amount)
        }
    )


def notify_food_preparing(order):
    """Notify customer when food is being prepared"""
    send_notification(
        user=order.customer,
        notification_type='food_preparing',
        title='Your Food is Being Prepared',
        message=f'Your order #{order.order_number} from {order.restaurant.name} is now being prepared!',
        channels=['in_app', 'sms'],
        reference_id=str(order.id),
        reference_type='FoodOrder'
    )


def notify_food_ready(order):
    """Notify customer when food is ready"""
    send_notification(
        user=order.customer,
        notification_type='food_ready',
        title='Food Ready!',
        message=f'Your order #{order.order_number} is ready for pickup/delivery!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='FoodOrder'
    )


def notify_food_out_for_delivery(order):
    """Notify customer when food is out for delivery"""
    send_notification(
        user=order.customer,
        notification_type='food_out_for_delivery',
        title='Food on the Way!',
        message=f'Your order #{order.order_number} is out for delivery. It will arrive soon!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='FoodOrder'
    )


def notify_food_delivered(order):
    """Notify customer when food is delivered"""
    send_notification(
        user=order.customer,
        notification_type='food_delivered',
        title='Order Delivered!',
        message=f'Your order #{order.order_number} has been delivered. Enjoy your meal from {order.restaurant.name}!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(order.id),
        reference_type='FoodOrder'
    )
