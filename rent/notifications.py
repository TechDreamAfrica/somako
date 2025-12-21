from accounts.notification_service import send_notification


def notify_rental_booked(booking):
    """Notify owner when new booking is made"""
    owner = None

    if hasattr(booking, 'property') and booking.property:
        owner = booking.property.owner
        item_name = booking.property.title
        item_type = "property"
    elif hasattr(booking, 'equipment') and booking.equipment:
        owner = booking.equipment.owner
        item_name = booking.equipment.name
        item_type = "equipment"

    if owner:
        # Use the correct field names based on the booking model
        renter = booking.renter if hasattr(booking, 'renter') else booking.customer
        total_amount = booking.total_amount if hasattr(booking, 'total_amount') else booking.total_price
        
        send_notification(
            user=owner,
            notification_type='rental_booked',
            title=f'New {item_type.title()} Booking!',
            message=f'New booking for your {item_name}. Customer: {renter.get_full_name() or renter.username}. Dates: {booking.start_date.strftime("%b %d")} - {booking.end_date.strftime("%b %d, %Y")}. Total: GHS {total_amount}',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(booking.id),
            reference_type='RentalBooking',
            data={
                'booking_id': str(booking.id),
                'item_type': item_type,
                'item_name': item_name,
                'total': str(total_amount),
                'start_date': booking.start_date.isoformat(),
                'end_date': booking.end_date.isoformat()
            }
        )


def notify_rental_confirmed(booking):
    """Notify customer when booking is confirmed"""
    item_name = booking.property.title if booking.property else booking.equipment.name
    item_type = "property" if booking.property else "equipment"

    send_notification(
        user=booking.customer,
        notification_type='rental_confirmed',
        title='Booking Confirmed!',
        message=f'Your {item_type} booking for {item_name} has been confirmed! Dates: {booking.start_date.strftime("%b %d")} - {booking.end_date.strftime("%b %d, %Y")}. Total: GHS {booking.total_price}',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(booking.id),
        reference_type='RentalBooking',
        data={
            'booking_id': str(booking.id),
            'item_name': item_name,
            'total': str(booking.total_price)
        }
    )


def notify_rental_started(booking):
    """Notify both parties when rental period starts"""
    item_name = booking.property.title if booking.property else booking.equipment.name
    item_type = "property" if booking.property else "equipment"

    # Notify customer
    send_notification(
        user=booking.customer,
        notification_type='rental_started',
        title='Rental Started!',
        message=f'Your {item_type} rental for {item_name} has started. Enjoy until {booking.end_date.strftime("%b %d, %Y")}!',
        channels=['in_app', 'sms'],
        reference_id=str(booking.id),
        reference_type='RentalBooking'
    )

    # Notify owner
    owner = booking.property.owner if booking.property else booking.equipment.owner
    if owner:
        send_notification(
            user=owner,
            notification_type='rental_started',
            title='Rental Period Started',
            message=f'Rental period for your {item_name} has started with {booking.customer.get_full_name() or booking.customer.username}.',
            channels=['in_app'],
            reference_id=str(booking.id),
            reference_type='RentalBooking'
        )


def notify_rental_ending_soon(booking, days_left):
    """Notify customer when rental is ending soon"""
    item_name = booking.property.title if booking.property else booking.equipment.name

    send_notification(
        user=booking.customer,
        notification_type='rental_started',
        title='Rental Ending Soon',
        message=f'Your rental for {item_name} ends in {days_left} day(s) on {booking.end_date.strftime("%b %d, %Y")}.',
        channels=['in_app', 'sms'],
        reference_id=str(booking.id),
        reference_type='RentalBooking'
    )


def notify_rental_ended(booking):
    """Notify both parties when rental ends"""
    item_name = booking.property.title if booking.property else booking.equipment.name
    item_type = "property" if booking.property else "equipment"

    # Notify customer
    send_notification(
        user=booking.customer,
        notification_type='rental_ended',
        title='Rental Ended',
        message=f'Your {item_type} rental for {item_name} has ended. Thank you for using Soma Ko!',
        channels=['in_app', 'sms', 'whatsapp'],
        reference_id=str(booking.id),
        reference_type='RentalBooking'
    )

    # Notify owner
    owner = booking.property.owner if booking.property else booking.equipment.owner
    if owner:
        send_notification(
            user=owner,
            notification_type='rental_ended',
            title='Rental Period Ended',
            message=f'Rental period for your {item_name} with {booking.customer.get_full_name() or booking.customer.username} has ended.',
            channels=['in_app', 'sms'],
            reference_id=str(booking.id),
            reference_type='RentalBooking'
        )


def notify_rental_cancelled(booking, cancelled_by):
    """Notify when booking is cancelled"""
    item_name = booking.property.title if booking.property else booking.equipment.name
    owner = booking.property.owner if booking.property else booking.equipment.owner

    if cancelled_by == booking.customer:
        # Notify owner
        if owner:
            send_notification(
                user=owner,
                notification_type='rental_cancelled',
                title='Booking Cancelled',
                message=f'Booking for your {item_name} has been cancelled by the customer.',
                channels=['in_app', 'sms', 'whatsapp'],
                reference_id=str(booking.id),
                reference_type='RentalBooking'
            )
    elif owner and cancelled_by == owner:
        # Notify customer
        send_notification(
            user=booking.customer,
            notification_type='rental_cancelled',
            title='Booking Cancelled',
            message=f'Your booking for {item_name} has been cancelled by the owner. You will receive a full refund.',
            channels=['in_app', 'sms', 'whatsapp'],
            reference_id=str(booking.id),
            reference_type='RentalBooking'
        )
