"""
Arkesel SMS Integration for Soma Ko Logistics
Handles sending SMS notifications for orders and ride updates
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ArkeselSMS:
    """Arkesel SMS API Integration"""

    def __init__(self):
        self.api_key = getattr(settings, 'ARKESEL_API_KEY', '')
        self.sender_id = getattr(settings, 'ARKESEL_SENDER_ID', 'Soma Ko')
        self.base_url = 'https://sms.arkesel.com/api/v2/sms/send'

    def send_sms(self, recipient, message):
        """
        Send SMS via Arkesel API

        Args:
            recipient (str): Phone number in format +233XXXXXXXXX or 0XXXXXXXXX
            message (str): SMS message content

        Returns:
            dict: Response from Arkesel API
        """
        if not self.api_key:
            logger.warning("Arkesel API key not configured. SMS not sent.")
            return {'success': False, 'message': 'API key not configured'}

        # Format phone number to Ghana format
        phone = self._format_phone_number(recipient)

        if not phone:
            logger.error(f"Invalid phone number format: {recipient}")
            return {'success': False, 'message': 'Invalid phone number'}

        # Arkesel expects api-key in headers
        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'sender': self.sender_id,
            'recipients': [phone],  # Must be an array
            'message': message
        }

        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
            response_data = response.json()

            # Arkesel returns status: 'success' or 'error'
            if response.status_code == 200 and response_data.get('status') == 'success':
                logger.info(f"SMS sent successfully to {phone}")
                return {'success': True, 'data': response_data}
            else:
                logger.error(f"SMS failed: {response_data}")
                return {'success': False, 'message': response_data.get('message', 'Unknown error')}

        except requests.exceptions.RequestException as e:
            logger.error(f"SMS API request failed: {str(e)}")
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in SMS sending: {str(e)}")
            return {'success': False, 'message': str(e)}

    def _format_phone_number(self, phone):
        """
        Format phone number to Arkesel's expected format

        Args:
            phone (str): Phone number

        Returns:
            str: Formatted phone number or None if invalid
        """
        if not phone:
            return None

        # Remove spaces and dashes
        phone = phone.replace(' ', '').replace('-', '')

        # Convert to Ghana format
        if phone.startswith('0'):
            # Convert 0XXXXXXXXX to 233XXXXXXXXX
            phone = '233' + phone[1:]
        elif phone.startswith('+233'):
            # Remove + prefix
            phone = phone[1:]
        elif phone.startswith('233'):
            # Already in correct format
            pass
        else:
            # Invalid format
            return None

        # Validate length (233 + 9 digits = 12 digits)
        if len(phone) == 12 and phone.startswith('233'):
            return phone

        return None


def send_order_notification(order, status_change=False):
    """
    Send SMS notification to restaurant owner about new order or status change

    Args:
        order: Order instance
        status_change (bool): Whether this is a status change notification

    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()

    # Get restaurant owner's phone number
    restaurant = order.restaurant
    if not restaurant.phone:
        logger.warning(f"No phone number for restaurant {restaurant.name}")
        return {'success': False, 'message': 'No phone number'}

    # Build message
    if status_change:
        message = (
            f"SOMA KO FOOD - Order #{order.order_number} status updated to {order.get_status_display()}. "
            f"Customer: {order.customer.get_full_name() or order.customer.username}. "
            f"Total: GHS {order.total_amount}."
        )
    else:
        # Get customer contact
        customer_phone = order.delivery_phone or getattr(order.customer, 'phone_number', 'N/A')
        customer_name = order.customer.get_full_name() or order.customer.username
        
        message = (
            f"SOMA KO FOOD - New Order #{order.order_number}! "
            f"Customer: {customer_name}. "
            f"Phone: {customer_phone}. "
            f"Items: {order.items.count()}. "
            f"Total: GHS {order.total_amount}. "
            f"Delivery: {order.delivery_city}."
        )

    return sms.send_sms(restaurant.phone, message)


def send_customer_order_confirmation(order):
    """
    Send SMS confirmation to customer when order is placed

    Args:
        order: Order instance

    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()

    # Get customer's phone number
    customer_phone = order.delivery_phone or getattr(order.customer, 'phone_number', None)
    
    if not customer_phone:
        logger.warning(f"No phone number for customer {order.customer.username}")
        return {'success': False, 'message': 'No customer phone number'}

    # Build confirmation message
    message = (
        f"SOMA KO - Order Confirmed! "
        f"Order #{order.order_number} "
        f"from {order.restaurant.name}. "
        f"Total: GHS {order.total_amount}. "
        f"Delivery to: {order.delivery_city}. "
        f"Track your order in the app. Thank you!"
    )

    return sms.send_sms(customer_phone, message)


def send_customer_order_status_update(order, new_status):
    """
    Send SMS notification to customer when order status is updated

    Args:
        order: Order instance
        new_status (str): New order status

    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()

    # Get customer's phone number
    customer_phone = order.delivery_phone or getattr(order.customer, 'phone_number', None)
    
    if not customer_phone:
        logger.warning(f"No phone number for customer {order.customer.username}")
        return {'success': False, 'message': 'No customer phone number'}

    # Build status-specific messages
    if new_status == 'confirmed':
        message = (
            f"SOMA KO - Order #{order.order_number} has been CONFIRMED by {order.restaurant.name}! "
            f"Your delicious meal is being prepared. "
            f"Track your order in the app. "
            f"Total: GHS {order.total_amount}."
        )
    elif new_status == 'delivered':
        message = (
            f"SOMA KO - Order #{order.order_number} has been DELIVERED! "
            f"We hope you enjoy your meal from {order.restaurant.name}. "
            f"Please rate your experience in the app. "
            f"Thank you for choosing Soma Ko!"
        )
    elif new_status == 'preparing':
        message = (
            f"SOMA KO - Your order #{order.order_number} from {order.restaurant.name} "
            f"is now being PREPARED. It will be ready soon!"
        )
    elif new_status == 'ready':
        message = (
            f"SOMA KO - Order #{order.order_number} is READY for pickup/delivery! "
            f"Your meal from {order.restaurant.name} is on its way."
        )
    elif new_status == 'on_the_way':
        message = (
            f"SOMA KO - Order #{order.order_number} is ON THE WAY! "
            f"Your delivery from {order.restaurant.name} will arrive soon."
        )
    elif new_status == 'cancelled':
        message = (
            f"SOMA KO - Order #{order.order_number} has been CANCELLED. "
            f"Reason: {order.cancellation_reason or 'Not specified'}. "
            f"If you have questions, please contact support."
        )
    else:
        # Generic status update
        message = (
            f"SOMA KO - Order #{order.order_number} status updated to {new_status.upper()}. "
            f"Track your order in the app for more details."
        )

    return sms.send_sms(customer_phone, message)


def send_ride_notification(ride, status_change=False):
    """
    Send SMS notification about ride to passenger or driver

    Args:
        ride: Ride instance
        status_change (bool): Whether this is a status change notification

    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()

    # Send to passenger
    if ride.passenger and ride.passenger.phone_number:
        if status_change:
            message = (
                f"SOMA KO RIDE - Ride #{ride.ride_id} status: {ride.get_status_display()}. "
            )
            if ride.driver:
                message += f"Driver: {ride.driver.user.get_full_name()}. "
            message += f"View: {settings.SITE_URL}/pwa/ride/rides/{ride.id}/"
        else:
            message = (
                f"SOMA KO RIDE - Ride #{ride.ride_id} booked! "
                f"From: {ride.pickup_address[:30]}... "
                f"To: {ride.dropoff_address[:30]}... "
                f"Fare: GHS {ride.total_fare}. "
                f"Track: {settings.SITE_URL}/pwa/ride/rides/{ride.id}/track/"
            )

        sms.send_sms(ride.passenger.phone_number, message)

    # Send to driver if assigned
    if ride.driver and ride.driver.user.phone_number:
        if status_change:
            message = (
                f"SOMA KO RIDE - Ride #{ride.ride_id} status updated: {ride.get_status_display()}. "
                f"Passenger: {ride.passenger.get_full_name()}. "
                f"View: {settings.SITE_URL}/pwa/ride/rides/{ride.id}/"
            )
            sms.send_sms(ride.driver.user.phone_number, message)

    return {'success': True, 'message': 'Notifications sent'}


def send_custom_sms(phone_number, message):
    """
    Send a custom SMS message

    Args:
        phone_number (str): Recipient phone number
        message (str): SMS message content

    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()
    return sms.send_sms(phone_number, message)


def send_driver_ride_notification(driver, ride):
    """
    Send SMS notification to driver when a new ride is requested
    
    Args:
        driver: DriverProfile instance
        ride: Ride instance
        
    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()
    
    # Get driver's phone number from profile
    driver_phone = driver.user.profile.phone_number if hasattr(driver.user, 'profile') and driver.user.profile.phone_number else None
    
    if not driver_phone:
        logger.warning(f"No phone number for driver {driver.user.username}")
        return {'success': False, 'message': 'No driver phone number'}
    
    # Build notification message
    passenger_name = ride.passenger.get_full_name() or ride.passenger.username
    pickup_short = ride.pickup_address[:40] + ('...' if len(ride.pickup_address) > 40 else '')
    dropoff_short = ride.dropoff_address[:40] + ('...' if len(ride.dropoff_address) > 40 else '')
    
    message = (
        f"SOMA KO RIDE - New Ride Request! "
        f"Ride #{ride.ride_id}. "
        f"Passenger: {passenger_name}. "
        f"From: {pickup_short}. "
        f"To: {dropoff_short}. "
        f"Distance: {ride.estimated_distance_km} km. "
        f"Fare: GHS {ride.total_fare}. "
        f"Accept in app now!"
    )
    
    result = sms.send_sms(driver_phone, message)
    
    if result.get('success'):
        logger.info(f"SMS sent to driver {driver.user.username} for ride {ride.ride_id}")
    else:
        logger.error(f"Failed to send SMS to driver {driver.user.username}: {result.get('message')}")
    
    return result


def send_nearby_drivers_notification(ride, nearby_drivers):
    """
    Send SMS notifications to all nearby available drivers when a ride is requested
    
    Args:
        ride: Ride instance
        nearby_drivers: List or QuerySet of DriverProfile instances
        
    Returns:
        dict: Summary of SMS send results
    """
    results = {
        'success_count': 0,
        'failed_count': 0,
        'total': 0,
        'details': []
    }
    
    for driver in nearby_drivers:
        result = send_driver_ride_notification(driver, ride)
        results['total'] += 1
        
        if result.get('success'):
            results['success_count'] += 1
        else:
            results['failed_count'] += 1
        
        results['details'].append({
            'driver': driver.user.username,
            'success': result.get('success'),
            'message': result.get('message')
        })
    
    logger.info(
        f"Notified {results['success_count']}/{results['total']} drivers for ride {ride.ride_id}"
    )
    
    return results


def send_passenger_ride_confirmation(passenger, ride):
    """
    Send SMS confirmation to passenger when ride is requested
    
    Args:
        passenger: User instance (passenger)
        ride: Ride instance
        
    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()
    
    # Get passenger's phone number
    passenger_phone = passenger.profile.phone_number if hasattr(passenger, 'profile') and passenger.profile.phone_number else None
    
    if not passenger_phone:
        logger.warning(f"Passenger {passenger.username} has no phone number")
        return {'success': False, 'message': 'No phone number'}
    
    # Format message
    driver_name = ride.driver.user.get_full_name() if ride.driver else "a driver"
    message = (
        f"SOMA KO RIDE - Ride Request Sent! "
        f"Ride #{ride.ride_id}. "
        f"Driver: {driver_name}. "
        f"From: {ride.pickup_address}. "
        f"To: {ride.dropoff_address}. "
        f"Fare: GHS {ride.total_fare}. "
        f"Waiting for driver to accept. Track in app."
    )
    
    result = sms.send_sms(passenger_phone, message)
    
    if result.get('success'):
        logger.info(f"Ride request confirmation SMS sent to passenger {passenger.username} for ride {ride.ride_id}")
    else:
        logger.error(f"Failed to send ride request confirmation to passenger {passenger.username}: {result.get('message')}")
    
    return result


def send_passenger_driver_accepted(passenger, ride):
    """
    Send SMS to passenger when driver accepts the ride
    
    Args:
        passenger: User instance (passenger)
        ride: Ride instance
        
    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()
    
    # Get passenger's phone number
    passenger_phone = passenger.profile.phone_number if hasattr(passenger, 'profile') and passenger.profile.phone_number else None
    
    if not passenger_phone:
        logger.warning(f"Passenger {passenger.username} has no phone number")
        return {'success': False, 'message': 'No phone number'}
    
    # Format message
    driver_name = ride.driver.user.get_full_name() if ride.driver else "A driver"
    vehicle_info = f"{ride.vehicle.make} {ride.vehicle.model}" if ride.vehicle else "vehicle"
    message = (
        f"SOMA KO RIDE - Driver Accepted! "
        f"{driver_name} has accepted your ride #{ride.ride_id}. "
        f"Vehicle: {vehicle_info}. "
        f"Driver will arrive shortly. Track in app."
    )
    
    result = sms.send_sms(passenger_phone, message)
    
    if result.get('success'):
        logger.info(f"Driver acceptance SMS sent to passenger {passenger.username} for ride {ride.ride_id}")
    else:
        logger.error(f"Failed to send driver acceptance SMS to passenger {passenger.username}: {result.get('message')}")
    
    return result


def send_passenger_ride_completed(passenger, ride):
    """
    Send SMS to passenger when ride is completed
    
    Args:
        passenger: User instance (passenger)
        ride: Ride instance
        
    Returns:
        dict: SMS send result
    """
    sms = ArkeselSMS()
    
    # Get passenger's phone number
    passenger_phone = passenger.profile.phone_number if hasattr(passenger, 'profile') and passenger.profile.phone_number else None
    
    if not passenger_phone:
        logger.warning(f"Passenger {passenger.username} has no phone number")
        return {'success': False, 'message': 'No phone number'}
    
    # Format message
    message = (
        f"SOMA KO RIDE - Ride Completed! "
        f"Ride #{ride.ride_id} has been completed. "
        f"Fare: GHS {ride.total_fare}. "
        f"Please confirm completion and rate your driver in the app. Thank you!"
    )
    
    result = sms.send_sms(passenger_phone, message)
    
    if result.get('success'):
        logger.info(f"Ride completion SMS sent to passenger {passenger.username} for ride {ride.ride_id}")
    else:
        logger.error(f"Failed to send ride completion SMS to passenger {passenger.username}: {result.get('message')}")
    
    return result


def send_user_verification_code(user, code):
    """Send a 4-digit verification code to the user's phone AND email.

    Returns a dict with success flag and optional message.
    """
    sms = ArkeselSMS()

    # Prefer direct phone number fields commonly used in this project
    phone = None
    try:
        # Try user.profile.phone_number style first
        if hasattr(user, 'profile') and getattr(user.profile, 'phone_number', None):
            phone = user.profile.phone_number
    except Exception:
        phone = None

    # Fallback to User.phone_number field if present
    if not phone:
        phone = getattr(user, 'phone_number', None)

    message = f"SOMA KO - Your verification code is {code}. It expires in 15 minutes."
    
    logger.info(f"Attempting to send verification code to {user.username}. Phone: {phone}, Email: {getattr(user, 'email', 'N/A')}")

    sms_sent = False
    email_sent = False
    errors = []
    
    # Try SMS first if phone is available
    if phone:
        try:
            result = sms.send_sms(phone, message)
            if result.get('success'):
                logger.info(f"Verification code sent via SMS to {user.username} at {phone}")
                sms_sent = True
            else:
                error_msg = result.get('message', 'Unknown SMS error')
                logger.error(f"Failed to send verification SMS to {user.username} at {phone}: {error_msg}")
                errors.append(f"SMS: {error_msg}")
        except Exception as e:
            logger.error(f"SMS exception for {user.username}: {e}")
            errors.append(f"SMS: {str(e)}")
    else:
        logger.warning(f"No phone number available for {user.username}")

    # Always try to send email as well (backup)
    to_email = getattr(user, 'email', None)
    if to_email:
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings
            
            user_name = user.get_full_name() or user.username
            
            # HTML email content for verification code
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .code-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center; border: 2px dashed #8b5cf6; }}
                    .code {{ font-size: 36px; font-weight: bold; color: #8b5cf6; letter-spacing: 8px; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Verification Code</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {user_name}!</h2>
                        <p>Thank you for signing up with Soma Ko. To complete your registration, please use the verification code below:</p>
                        
                        <div class="code-box">
                            <p class="code">{code}</p>
                        </div>
                        
                        <p><strong>⏰ This code expires in 15 minutes.</strong></p>
                        
                        <p>If you didn't create an account with Soma Ko, please ignore this email.</p>
                        
                        <p>Best regards,<br><strong>The Soma Ko Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create email with both plain text and HTML
            email = EmailMultiAlternatives(
                subject="Your Soma Ko Verification Code",
                body=message,
                from_email=settings.EMAIL_HOST_USER,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Verification code emailed to {user.username} at {to_email}")
            email_sent = True
        except Exception as e:
            logger.error(f"Failed to email verification code to {user.username} at {to_email}: {e}")
            errors.append(f"Email: {str(e)}")
    else:
        logger.warning(f"No email address available for {user.username}")

    # Return success if either SMS or email was sent
    if sms_sent or email_sent:
        channels = []
        if sms_sent:
            channels.append('SMS')
        if email_sent:
            channels.append('email')
        return {'success': True, 'message': f'Code sent via {" and ".join(channels)}'}
    
    error_details = '; '.join(errors) if errors else 'No phone or email available'
    logger.warning(f"Failed to send verification code to {user.username} via any channel: {error_details}")
    return {'success': False, 'message': f'Failed to send verification code: {error_details}'}


def send_express_order_notification(express_order):
    """
    Send SMS notification to all recipients when an express order is created
    
    Args:
        express_order: ExpressOrder instance
        
    Returns:
        list: List of SMS send results for each recipient
    """
    if not express_order:
        return []
    
    sms = ArkeselSMS()
    results = []
    recipients = express_order.get_recipients()
    
    # Send SMS to each unique recipient
    for recipient in recipients:
        message = (
            f"📦 Hello {recipient['name']}!\n\n"
            f"A package has been sent to you via Soma Ko Express.\n\n"
            f"Order Number: {express_order.order_number}\n"
            f"Sender: {express_order.sender.get_full_name() or express_order.sender.username}\n"
            f"Expected Delivery: Soon\n\n"
            f"You will receive updates as your package moves through our delivery network.\n\n"
            f"Track your package at http://www.somako.org/pwa/express/\n"
            f"- Soma Ko Express Team"
        )
        
        try:
            result = sms.send_sms(recipient['phone'], message)
            result['recipient'] = recipient['name']
            result['phone'] = recipient['phone']
            results.append(result)
            logger.info(f"Express order notification sent to {recipient['name']} ({recipient['phone']})")
        except Exception as e:
            error_result = {
                'success': False,
                'message': str(e),
                'recipient': recipient['name'],
                'phone': recipient['phone']
            }
            results.append(error_result)
            logger.error(f"Failed to send express order notification to {recipient['name']}: {e}")
    
    return results


def send_express_order_status_update(express_order, new_status):
    """
    Send SMS notification to recipients when order status changes
    
    Args:
        express_order: ExpressOrder instance
        new_status: New status of the order
        
    Returns:
        list: List of SMS send results for each recipient
    """
    if not express_order:
        return []
    
    sms = ArkeselSMS()
    results = []
    recipients = express_order.get_recipients()
    
    # Status-specific messages
    status_messages = {
        'assigned': f"🚛 Your package order {express_order.order_number} has been assigned to a delivery driver and will be picked up soon.",
        'in_progress': f"📍 Your package order {express_order.order_number} is now in progress. The driver is collecting your items.",
        'completed': f"✅ Great news! Your package order {express_order.order_number} has been completed. All items have been delivered.",
        'cancelled': f"❌ Your package order {express_order.order_number} has been cancelled. Please contact us if you have any questions."
    }
    
    base_message = status_messages.get(new_status, f"📦 Your package order {express_order.order_number} status has been updated to: {new_status}")
    
    # Send SMS to each unique recipient
    for recipient in recipients:
        message = (
            f"Hello {recipient['name']}!\n\n"
            f"{base_message}\n\n"
            f"Track your order at http://www.somako.org/pwa/express/\n"
            f"- Soma Ko Express Team"
        )
        
        try:
            result = sms.send_sms(recipient['phone'], message)
            result['recipient'] = recipient['name']
            result['phone'] = recipient['phone']
            results.append(result)
            logger.info(f"Express order status update sent to {recipient['name']} ({recipient['phone']})")
        except Exception as e:
            error_result = {
                'success': False,
                'message': str(e),
                'recipient': recipient['name'],
                'phone': recipient['phone']
            }
            results.append(error_result)
            logger.error(f"Failed to send express order status update to {recipient['name']}: {e}")
    
    return results

def send_express_sender_notification(express_order, notification_type):
    """
    Send SMS notification to the sender of an express order
    
    Args:
        express_order: ExpressOrder instance
        notification_type: Type of notification ('submitted', 'assigned', 'in_progress', 'completed', 'cancelled')
        
    Returns:
        dict: SMS send result
    """
    if not express_order or not express_order.sender:
        return {'success': False, 'message': 'Invalid order or sender'}
    
    sender = express_order.sender
    sender_phone = getattr(sender, 'phone_number', None)
    
    if not sender_phone:
        return {'success': False, 'message': 'Sender phone number not available'}
    
    sms = ArkeselSMS()
    
    # Notification-specific messages for senders
    sender_messages = {
        'submitted': f"✅ Your express order {express_order.order_number} has been submitted successfully! We'll notify you when a driver is assigned.",
        'assigned': f"🚛 Good news! Your express order {express_order.order_number} has been assigned to a driver and pickup will begin soon.",
        'in_progress': f"📍 Your express order {express_order.order_number} is now in progress. The driver is collecting and delivering your items.",
        'completed': f"🎉 Excellent! Your express order {express_order.order_number} has been completed successfully. All items have been delivered.",
        'cancelled': f"❌ Your express order {express_order.order_number} has been cancelled. Contact support if you need assistance."
    }
    
    base_message = sender_messages.get(notification_type, f"📦 Your express order {express_order.order_number} status has been updated.")
    sender_name = sender.get_full_name() or sender.first_name or sender.username
    
    message = (
        f"Hello {sender_name}!\n\n"
        f"{base_message}\n\n"
        f"Order Details:\n"
        f"• Items: {express_order.items.count()}\n"
        f"• Total: GH₵{express_order.total_estimated_cost}\n\n"
        f"Track at http://www.somako.org/pwa/express/\n"
        f"- Soma Ko Express Team"
    )
    
    try:
        result = sms.send_sms(sender_phone, message)
        result['recipient'] = sender_name
        result['phone'] = sender_phone
        logger.info(f"Express order sender notification sent to {sender_name} ({sender_phone})")
        return result
    except Exception as e:
        error_result = {
            'success': False,
            'message': str(e),
            'recipient': sender_name,
            'phone': sender_phone
        }
        logger.error(f"Failed to send sender notification to {sender_name} ({sender_phone}): {str(e)}")
        return error_result

def send_express_driver_assignment_notification(express_order, driver):
    """
    Send SMS notification to driver when assigned to an express order
    
    Args:
        express_order: ExpressOrder instance
        driver: User instance (the assigned driver)
        
    Returns:
        dict: SMS send result
    """
    if not express_order or not driver:
        return {'success': False, 'message': 'Missing order or driver information'}
    
    # Get driver's phone number
    driver_phone = None
    
    # Try different ways to get driver's phone number
    if hasattr(driver, 'phone_number') and driver.phone_number:
        driver_phone = driver.phone_number
    elif hasattr(driver, 'profile') and hasattr(driver.profile, 'phone_number') and driver.profile.phone_number:
        driver_phone = driver.profile.phone_number
    elif hasattr(driver, 'delivery_driver_profile') and hasattr(driver.delivery_driver_profile, 'phone_number') and driver.delivery_driver_profile.phone_number:
        driver_phone = driver.delivery_driver_profile.phone_number
    
    if not driver_phone:
        logger.warning(f"No phone number found for driver {driver.username}")
        return {'success': False, 'message': f'No phone number for driver {driver.username}', 'driver': driver.username}
    
    # Get order details
    items_count = express_order.items.count()
    pickup_locations = list(express_order.items.values_list('pickup_address', flat=True).distinct())
    delivery_locations = list(express_order.items.values_list('delivery_address', flat=True).distinct())
    
    # Create driver notification message
    message = (
        f"🚛 Hello {driver.get_full_name() or driver.username}!\n\n"
        f"You have been assigned a new express delivery order.\n\n"
        f"Order Number: {express_order.order_number}\n"
        f"Items to Deliver: {items_count}\n"
        f"Sender: {express_order.sender.get_full_name() or express_order.sender.username}\n"
    )
    
    if pickup_locations:
        message += f"Pickup: {pickup_locations[0][:50]}{'...' if len(pickup_locations[0]) > 50 else ''}\n"
    
    if delivery_locations:
        message += f"Delivery: {delivery_locations[0][:50]}{'...' if len(delivery_locations[0]) > 50 else ''}\n"
    
    message += (
        f"\nPlease log in to your driver dashboard to view full details and start the delivery.\n\n"
        f"Dashboard: http://www.somako.org/pwa/express/\n"
        f"- Soma Ko Express Team"
    )
    
    sms = ArkeselSMS()
    
    try:
        result = sms.send_sms(driver_phone, message)
        result['driver'] = driver.get_full_name() or driver.username
        result['phone'] = driver_phone
        logger.info(f"Express order assignment notification sent to driver {driver.username} ({driver_phone})")
        return result
    except Exception as e:
        error_result = {
            'success': False,
            'message': str(e),
            'driver': driver.get_full_name() or driver.username,
            'phone': driver_phone
        }
        logger.error(f"Failed to send express order assignment notification to driver {driver.username}: {e}")
        return error_result


def send_shop_order_notification_to_seller(order):
    """
    Send SMS notification to shop owner(s) when a new order is placed
    
    Args:
        order: Order instance from shop.models
        
    Returns:
        list: List of SMS send results for each shop owner notified
    """
    if not order:
        return []
    
    sms = ArkeselSMS()
    results = []
    
    # Get unique shops from order items
    shops_notified = set()
    
    try:
        for item in order.items.all():
            # Get shop from variant -> product -> shop
            shop = None
            if item.variant and item.variant.product:
                shop = item.variant.product.shop
            
            if not shop or shop.id in shops_notified:
                continue
            
            shops_notified.add(shop.id)
            
            # Get shop owner's phone number
            owner = shop.owner
            owner_phone = getattr(owner, 'phone_number', None)
            
            if not owner_phone:
                logger.warning(f"Shop owner {owner.username} has no phone number. Cannot send order notification.")
                continue
            
            # Build order summary
            shop_items = [i for i in order.items.all() if i.variant and i.variant.product and i.variant.product.shop_id == shop.id]
            items_summary = ', '.join([f"{i.quantity}x {i.product_name[:20]}" for i in shop_items[:3]])
            if len(shop_items) > 3:
                items_summary += f" +{len(shop_items) - 3} more"
            
            # Calculate shop-specific total
            shop_total = sum(i.total_price for i in shop_items)
            
            message = (
                f"🛍️ NEW ORDER RECEIVED!\n\n"
                f"Order #: {order.order_number}\n"
                f"Shop: {shop.name}\n"
                f"Items: {items_summary}\n"
                f"Total: GHS {shop_total:.2f}\n"
                f"Customer: {order.user.get_full_name() or order.user.username}\n"
                f"Phone: {order.customer_phone or 'N/A'}\n\n"
                f"Please log in to your seller dashboard to process this order.\n"
                f"Dashboard: http://www.somako.org/shop/seller/\n"
                f"- Soma Ko Team"
            )
            
            try:
                result = sms.send_sms(owner_phone, message)
                result['shop'] = shop.name
                result['owner'] = owner.username
                results.append(result)
                logger.info(f"Shop order notification sent to {owner.username} for shop {shop.name}")
            except Exception as e:
                error_result = {
                    'success': False,
                    'message': str(e),
                    'shop': shop.name,
                    'owner': owner.username
                }
                results.append(error_result)
                logger.error(f"Failed to send order notification to {owner.username}: {e}")
    
    except Exception as e:
        logger.error(f"Error in send_shop_order_notification_to_seller: {e}")
    
    return results
