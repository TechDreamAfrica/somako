"""
Payment Models for Paystack Integration
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Payment(models.Model):
    """
    Track all payment transactions across different apps
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('paystack', 'Paystack'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
    ]

    # Payment source apps
    SOURCE_APP_CHOICES = [
        ('rent', 'Rent'),
        ('food', 'Food'),
        ('shop', 'Shop'),
        ('pharmacy', 'Pharmacy'),
        ('ride', 'Ride'),
        ('subscription', 'Subscription'),
    ]

    # Basic Information
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Source Information
    source_app = models.CharField(max_length=20, choices=SOURCE_APP_CHOICES)
    order_id = models.CharField(max_length=100, null=True, blank=True)  # Reference to order in source app

    # Paystack Details
    paystack_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    paystack_access_code = models.CharField(max_length=100, null=True, blank=True)
    paystack_authorization_url = models.URLField(max_length=500, null=True, blank=True)

    # Transaction Details
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    gateway_response = models.TextField(null=True, blank=True)

    # Additional Information
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['source_app', 'order_id']),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.user.username} - {self.amount} {self.currency}"

    def mark_as_paid(self):
        """Mark payment as successful"""
        self.status = 'success'
        self.paid_at = timezone.now()
        self.save()

    def mark_as_failed(self, response=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if response:
            self.gateway_response = str(response)
        self.save()

    @property
    def is_successful(self):
        return self.status == 'success'

    @property
    def is_pending(self):
        return self.status == 'pending'


class PaystackWebhookLog(models.Model):
    """
    Log all webhook events from Paystack for debugging and audit
    """
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField()
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_logs'
    )
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"
