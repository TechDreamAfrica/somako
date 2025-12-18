from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class SubscriptionPlan(models.Model):
    """Subscription plans: Basic, Standard, Premium"""

    PLAN_TYPES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')

    # Features
    max_listings = models.IntegerField(help_text="Maximum number of active listings (-1 for unlimited)")
    featured_listings = models.IntegerField(default=0, help_text="Number of featured listings allowed")
    priority_support = models.BooleanField(default=False)
    analytics_access = models.BooleanField(default=False)
    verification_badge = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Commission rate percentage")

    # Visibility
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def __str__(self):
        return f"{self.display_name} - GHS {self.price}/month"


class UserSubscription(models.Model):
    """User's subscription status and history"""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Payment'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, related_name='subscriptions')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    next_billing_date = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Auto-renewal
    auto_renew = models.BooleanField(default=True)

    # Payment tracking
    last_payment_date = models.DateTimeField(null=True, blank=True)
    last_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Usage tracking
    current_listings_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Subscription"
        verbose_name_plural = "User Subscriptions"

    def __str__(self):
        return f"{self.user.username} - {self.plan.display_name if self.plan else 'No Plan'} ({self.status})"

    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == 'active' and self.end_date and self.end_date > timezone.now()

    def days_remaining(self):
        """Calculate days remaining in subscription"""
        if self.end_date and self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0

    def can_create_listing(self):
        """Check if user can create new listing"""
        if not self.is_active():
            return False
        if self.plan.max_listings == -1:
            return True
        return self.current_listings_count < self.plan.max_listings

    def renew(self):
        """Renew subscription for another month"""
        if self.plan:
            self.start_date = timezone.now()
            self.end_date = timezone.now() + timedelta(days=30)
            self.next_billing_date = self.end_date
            self.status = 'active'
            self.last_payment_date = timezone.now()
            self.last_payment_amount = self.plan.price
            self.save()

    def cancel(self):
        """Cancel subscription"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.auto_renew = False
        self.save()


class SubscriptionHistory(models.Model):
    """Track subscription changes and payments"""

    ACTION_TYPES = [
        ('subscribed', 'Subscribed'),
        ('renewed', 'Renewed'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('payment', 'Payment'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription_history')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Subscription History"
        verbose_name_plural = "Subscription Histories"

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.created_at.strftime('%Y-%m-%d')}"
