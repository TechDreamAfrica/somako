"""
Email Utilities for Soma Ko Logistics
Handles sending various email notifications
"""

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_welcome_email(user):
    """
    Send welcome email to newly registered user

    Args:
        user: User instance

    Returns:
        bool: True if email sent successfully
    """
    subject = 'Welcome to Soma Ko Logistics!'

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
            .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #8b5cf6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Soma Ko!</h1>
                <p>Your All-in-One Logistics Platform</p>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username}! 👋</h2>
                <p>Thank you for joining Soma Ko Logistics. We're excited to have you on board!</p>

                <p>Your account has been successfully created. You now have access to all our services:</p>

                <div class="feature">
                    <strong>🚗 Ride Services</strong> - Book rides anytime, anywhere
                </div>
                <div class="feature">
                    <strong>🍔 Food Delivery</strong> - Order from your favorite restaurants
                </div>
                <div class="feature">
                    <strong>🏠 Rent Services</strong> - Find your perfect rental
                </div>
                <div class="feature">
                    <strong>🛍️ Shopping</strong> - Browse and shop products
                </div>

                <center>
                    <a href="{settings.SITE_URL}" class="button">Explore Soma Ko</a>
                </center>

                <p style="margin-top: 30px;">If you have any questions or need assistance, feel free to contact our support team at <a href="mailto:support@somako.com">support@somako.com</a></p>

                <p>Best regards,<br><strong>The Soma Ko Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
                <p>Ghana | <a href="{settings.SITE_URL}">www.somako.org</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Welcome to Soma Ko Logistics!

    Hello {user.get_full_name() or user.username},

    Thank you for joining Soma Ko Logistics. We're excited to have you on board!

    Your account has been successfully created. You now have access to all our services:

    🚗 Ride Services - Book rides anytime, anywhere
    🍔 Food Delivery - Order from your favorite restaurants
    🏠 Rent Services - Find your perfect rental
    🛍️ Shopping - Browse and shop products

    Visit: {settings.SITE_URL}

    If you have any questions or need assistance, contact us at support@somako.com

    Best regards,
    The Soma Ko Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, reset_link):
    """
    Send password reset email

    Args:
        user: User instance
        reset_link (str): Password reset link

    Returns:
        bool: True if email sent successfully
    """
    subject = 'Reset Your Soma Ko Password'

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username},</h2>
                <p>We received a request to reset your Soma Ko account password.</p>

                <p>Click the button below to reset your password:</p>

                <center>
                    <a href="{reset_link}" class="button">Reset Password</a>
                </center>

                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul>
                        <li>This link will expire in 24 hours</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Never share your password with anyone</li>
                    </ul>
                </div>

                <p>Or copy and paste this link into your browser:<br>
                <a href="{reset_link}">{reset_link}</a></p>

                <p style="margin-top: 30px;">If you're having trouble, contact our support team at <a href="mailto:support@somako.com">support@somako.com</a></p>

                <p>Best regards,<br><strong>The Soma Ko Security Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Password Reset Request

    Hello {user.get_full_name() or user.username},

    We received a request to reset your Soma Ko account password.

    Click the link below to reset your password:
    {reset_link}

    Security Notice:
    - This link will expire in 24 hours
    - If you didn't request this reset, please ignore this email
    - Never share your password with anyone

    If you're having trouble, contact us at support@somako.com

    Best regards,
    The Soma Ko Security Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False


def send_login_notification_email(user, request):
    """
    Send email notification when user logs in

    Args:
        user: User instance
        request: Django request object

    Returns:
        bool: True if email sent successfully
    """
    from django.utils import timezone
    
    subject = 'New Login to Your Soma Ko Account'

    # Get client info
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR', 'Unknown')
    
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown device')
    login_time = timezone.now().strftime('%B %d, %Y at %I:%M %p')

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #3b82f6; }}
            .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 New Login Detected</h1>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username},</h2>
                <p>We detected a new login to your Soma Ko account.</p>

                <div class="info-box">
                    <strong>📅 Date & Time:</strong> {login_time}<br>
                    <strong>🌐 IP Address:</strong> {ip_address}<br>
                    <strong>💻 Device:</strong> {user_agent[:100]}...
                </div>

                <div class="warning">
                    <strong>⚠️ Was this you?</strong><br>
                    If you recognize this login, no action is needed.<br>
                    If you don't recognize this activity, please secure your account immediately.
                </div>

                <center>
                    <a href="{settings.SITE_URL}/accounts/password/change/" class="button">Secure My Account</a>
                </center>

                <p style="margin-top: 30px;"><strong>Security Tips:</strong></p>
                <ul>
                    <li>Never share your password with anyone</li>
                    <li>Use a strong, unique password</li>
                    <li>Enable two-factor authentication when available</li>
                    <li>Log out from shared devices</li>
                </ul>

                <p>If you need help, contact us at <a href="mailto:support@somako.com">support@somako.com</a></p>

                <p>Best regards,<br><strong>The Soma Ko Security Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    New Login to Your Soma Ko Account

    Hello {user.get_full_name() or user.username},

    We detected a new login to your Soma Ko account.

    Login Details:
    - Date & Time: {login_time}
    - IP Address: {ip_address}
    - Device: {user_agent[:100]}

    Was this you?
    If you recognize this login, no action is needed.
    If you don't recognize this activity, please secure your account immediately.

    Secure your account: {settings.SITE_URL}/accounts/password/change/

    Security Tips:
    - Never share your password with anyone
    - Use a strong, unique password
    - Enable two-factor authentication when available
    - Log out from shared devices

    If you need help, contact us at support@somako.com

    Best regards,
    The Soma Ko Security Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        if user.email:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Login notification email sent to {user.email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send login notification email to {user.email}: {str(e)}")
        return False


def send_password_changed_email(user, request):
    """
    Send email notification when password is successfully changed

    Args:
        user: User instance
        request: Django request object

    Returns:
        bool: True if email sent successfully
    """
    from django.utils import timezone
    
    subject = 'Password Changed Successfully - Soma Ko'

    # Get client info
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR', 'Unknown')
    
    change_time = timezone.now().strftime('%B %d, %Y at %I:%M %p')

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .success-box {{ background: #d1fae5; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #10b981; text-align: center; }}
            .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #10b981; }}
            .warning {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Password Changed</h1>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username},</h2>
                
                <div class="success-box">
                    <h3 style="margin: 0; color: #059669;">✓ Password Successfully Changed</h3>
                    <p style="margin: 10px 0 0 0;">Your Soma Ko account password has been updated.</p>
                </div>

                <div class="info-box">
                    <strong>📅 Changed On:</strong> {change_time}<br>
                    <strong>🌐 From IP:</strong> {ip_address}
                </div>

                <div class="warning">
                    <strong>⚠️ Didn't make this change?</strong><br>
                    If you didn't change your password, your account may be compromised.<br>
                    Please contact our support team immediately and reset your password.
                    
                    <center>
                        <a href="mailto:support@somako.com" class="button">Contact Support</a>
                    </center>
                </div>

                <p style="margin-top: 30px;"><strong>Security Reminder:</strong></p>
                <ul>
                    <li>Never share your password with anyone</li>
                    <li>Use a strong, unique password for each service</li>
                    <li>Be cautious of phishing attempts</li>
                    <li>Keep your recovery email and phone number up to date</li>
                </ul>

                <p>Best regards,<br><strong>The Soma Ko Security Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Password Changed Successfully

    Hello {user.get_full_name() or user.username},

    Your Soma Ko account password has been successfully changed.

    Change Details:
    - Changed On: {change_time}
    - From IP: {ip_address}

    Didn't make this change?
    If you didn't change your password, your account may be compromised.
    Please contact our support team immediately at support@somako.com

    Security Reminder:
    - Never share your password with anyone
    - Use a strong, unique password for each service
    - Be cautious of phishing attempts
    - Keep your recovery email and phone number up to date

    Best regards,
    The Soma Ko Security Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        if user.email:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Password changed notification email sent to {user.email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send password changed notification to {user.email}: {str(e)}")
        return False


def send_email_verification_email(user, verification_link):
    """
    Send email verification link to user

    Args:
        user: User instance
        verification_link: Email verification URL

    Returns:
        bool: True if email sent successfully
    """
    subject = 'Verify Your Soma Ko Email Address'

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 16px; font-weight: bold; }}
            .info-box {{ background: #ede9fe; padding: 15px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #8b5cf6; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📧 Verify Your Email</h1>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username}!</h2>
                <p>Thank you for signing up with Soma Ko. We're excited to have you on board!</p>

                <p>To complete your registration and activate your account, please verify your email address by clicking the button below:</p>

                <center>
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                </center>

                <div class="info-box">
                    <strong>ℹ️ Important:</strong>
                    <ul style="margin: 10px 0;">
                        <li>This verification link will expire in 24 hours</li>
                        <li>If you didn't create an account, you can safely ignore this email</li>
                        <li>After verification, you'll have full access to all Soma Ko services</li>
                    </ul>
                </div>

                <p>Or copy and paste this link into your browser:<br>
                <a href="{verification_link}" style="word-break: break-all; color: #8b5cf6;">{verification_link}</a></p>

                <p style="margin-top: 30px;">Need help? Contact us at <a href="mailto:support@somako.com">support@somako.com</a></p>

                <p>Best regards,<br><strong>The Soma Ko Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Verify Your Soma Ko Email Address

    Hello {user.get_full_name() or user.username},

    Thank you for signing up with Soma Ko. We're excited to have you on board!

    To complete your registration and activate your account, please verify your email address by clicking the link below:

    {verification_link}

    Important:
    - This verification link will expire in 24 hours
    - If you didn't create an account, you can safely ignore this email
    - After verification, you'll have full access to all Soma Ko services

    Need help? Contact us at support@somako.com

    Best regards,
    The Soma Ko Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        if user.email:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email verification link sent to {user.email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send email verification to {user.email}: {str(e)}")
        return False


def send_account_locked_email(user, reason='Multiple failed login attempts'):
    """
    Send email notification when account is locked

    Args:
        user: User instance
        reason: Reason for account lock

    Returns:
        bool: True if email sent successfully
    """
    from django.utils import timezone
    
    subject = '🔒 Your Soma Ko Account Has Been Locked'
    lock_time = timezone.now().strftime('%B %d, %Y at %I:%M %p')

    # HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .alert-box {{ background: #fee2e2; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #ef4444; }}
            .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 8px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 Account Locked</h1>
            </div>
            <div class="content">
                <h2>Hello {user.get_full_name() or user.username},</h2>
                
                <div class="alert-box">
                    <h3 style="margin: 0; color: #dc2626;">⚠️ Your Account Has Been Locked</h3>
                    <p style="margin: 10px 0 0 0;">For your security, your Soma Ko account has been temporarily locked.</p>
                </div>

                <div class="info-box">
                    <strong>📅 Locked On:</strong> {lock_time}<br>
                    <strong>🔍 Reason:</strong> {reason}
                </div>

                <p><strong>What happened?</strong></p>
                <p>Your account was automatically locked due to suspicious activity or security concerns to protect your information.</p>

                <p><strong>How to unlock your account:</strong></p>
                <ol>
                    <li>Click the button below to reset your password</li>
                    <li>Follow the instructions in the password reset email</li>
                    <li>Your account will be unlocked once you set a new password</li>
                </ol>

                <center>
                    <a href="{settings.SITE_URL}/accounts/password/reset/" class="button">Unlock My Account</a>
                </center>

                <p style="margin-top: 30px;">If you need immediate assistance, please contact our support team at <a href="mailto:support@somako.com">support@somako.com</a></p>

                <p>Best regards,<br><strong>The Soma Ko Security Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Soma Ko Logistics. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Your Soma Ko Account Has Been Locked

    Hello {user.get_full_name() or user.username},

    For your security, your Soma Ko account has been temporarily locked.

    Locked On: {lock_time}
    Reason: {reason}

    What happened?
    Your account was automatically locked due to suspicious activity or security concerns to protect your information.

    How to unlock your account:
    1. Visit {settings.SITE_URL}/accounts/password/reset/
    2. Follow the instructions in the password reset email
    3. Your account will be unlocked once you set a new password

    If you need immediate assistance, please contact our support team at support@somako.com

    Best regards,
    The Soma Ko Security Team

    © 2025 Soma Ko Logistics. All rights reserved.
    """

    try:
        if user.email:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Account locked notification email sent to {user.email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send account locked notification to {user.email}: {str(e)}")
        return False


def send_order_confirmation_email(order):
    """
    Send order confirmation email to customer

    Args:
        order: Order instance

    Returns:
        bool: True if email sent successfully
    """
    subject = f'Order Confirmation #{order.order_number} - Soma Ko'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; }}
            .order-item {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .total {{ background: #fff7ed; padding: 15px; margin: 20px 0; border-radius: 8px; font-size: 18px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Order Confirmed!</h1>
                <p>Order #{order.order_number}</p>
            </div>
            <div class="content">
                <h2>Thank you for your order!</h2>
                <p>Your order from {order.restaurant.name} has been confirmed.</p>

                <p><strong>Delivery Address:</strong> {order.delivery_address}</p>
                <p><strong>Delivery Phone:</strong> {order.delivery_phone}</p>

                <h3>Order Items:</h3>
                {"".join([f'<div class="order-item">{item.menu_item.name} x {item.quantity} - GHS {item.price}</div>' for item in order.items.all()])}

                <div class="total">
                    Total Amount: GHS {order.total_amount}
                </div>

                <p>Track your order: <a href="{settings.SITE_URL}/pwa/food/orders/{order.order_number}/track/">Track Order</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Order Confirmed!

    Order #{order.order_number}

    Thank you for your order from {order.restaurant.name}!

    Delivery Address: {order.delivery_address}
    Delivery Phone: {order.delivery_phone}

    Total Amount: GHS {order.total_amount}

    Track your order: {settings.SITE_URL}/pwa/food/orders/{order.order_number}/track/
    """

    try:
        if order.customer.email:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[order.customer.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Order confirmation email sent to {order.customer.email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {str(e)}")
        return False
