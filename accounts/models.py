from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    # App-specific service roles
    SERVICE_ROLE_CHOICES = [
        # Rent app roles
        ('landlord', 'Landlord - List Properties'),
        ('equipment_owner', 'Equipment Owner - Rent Equipment'),

        # Shop app roles
        ('seller', 'Seller - Sell Products'),

        # Pharmacy app roles
        ('pharmacy_owner', 'Pharmacy Owner - Sell Medicine'),

        # Food app roles
        ('restaurant_owner', 'Restaurant Owner - Sell Food'),

        # Ride app roles
        ('driver', 'Driver - Provide Rides'),
        ('rider', 'Rider - Book Rides'),

        # Express delivery roles
        ('delivery_driver', 'Delivery Driver - Express Deliveries'),

        # General roles
        ('general', 'General User'),
    ]

    # Multiple roles support - stores comma-separated role values
    service_roles = models.CharField(
        max_length=200,
        blank=True,
        default='general',
        help_text="Service roles (comma-separated): rider, restaurant_owner, etc."
    )
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        blank=True
    )
    location = models.CharField(max_length=100, blank=True)
    profile_picture = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Direct profile picture URL from any image hosting service"
    )
    bio = models.TextField(max_length=500, blank=True)
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional settings fields
    email_notifications = models.BooleanField(default=True)
    profile_visibility = models.BooleanField(default=True)

    def __str__(self):
        roles = self.get_roles_list()
        role_display = ', '.join(roles) if roles else 'No roles'
        return f"{self.username} ({role_display})"

    def get_roles_list(self):
        """Return list of user's roles"""
        if self.service_roles:
            return [role.strip() for role in self.service_roles.split(',') if role.strip()]
        return []

    def has_role(self, role):
        """Check if user has a specific role"""
        # Ensure service_roles is treated as string, not object
        if not hasattr(self, 'service_roles') or not self.service_roles:
            return False
        return role in self.get_roles_list()

    def add_role(self, role):
        """Add a role to user"""
        roles = self.get_roles_list()
        if role not in roles and role in dict(self.SERVICE_ROLE_CHOICES).keys():
            roles.append(role)
            self.service_roles = ','.join(roles)
            return True
        return False
    
    # Backward compatibility properties to prevent attribute access errors
    @property
    def rider_role(self):
        """Backward compatibility - returns True if user has rider role"""
        return self.has_role('rider')
    
    @property
    def delivery_driver_role(self):
        """Backward compatibility - returns True if user has delivery_driver role"""
        return self.has_role('delivery_driver')

    def remove_role(self, role):
        """Remove a role from user"""
        roles = self.get_roles_list()
        if role in roles:
            roles.remove(role)
            self.service_roles = ','.join(roles) if roles else 'general'
            return True
        return False

    def get_roles_display(self):
        """Get display names for all roles"""
        roles_dict = dict(self.SERVICE_ROLE_CHOICES)
        return [roles_dict.get(role, role) for role in self.get_roles_list()]

    def get_primary_role(self):
        """Get the first/primary role"""
        roles = self.get_roles_list()
        return roles[0] if roles else 'general'

    def is_provider(self):
        """Check if user is a service provider (any provider role)"""
        provider_roles = ['landlord', 'equipment_owner', 'seller', 'pharmacy_owner',
                         'restaurant_owner', 'driver']
        return any(self.has_role(role) for role in provider_roles)

    def is_customer(self):
        """Check if user is a service customer (any customer role)"""
        customer_roles = ['tenant', 'equipment_renter', 'buyer', 'patient',
                         'customer', 'rider']
        return any(self.has_role(role) for role in customer_roles)


class RoleApplication(models.Model):
    """Model for users to apply for specific service roles"""

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_applications')
    role = models.CharField(max_length=50, choices=User.SERVICE_ROLE_CHOICES)

    # Application details
    reason = models.TextField(
        help_text="Why do you want this role?",
        blank=True
    )
    experience = models.TextField(
        help_text="Relevant experience or qualifications",
        blank=True
    )

    # Supporting documents
    document = models.FileField(
        upload_to='role_applications/',
        blank=True,
        null=True,
        help_text="Supporting document (license, certificate, etc.)"
    )

    # Status and review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    review_note = models.TextField(blank=True, help_text="Admin's review notes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Role Application"
        verbose_name_plural = "Role Applications"
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} ({self.status})"

    def approve(self, admin_user, note=''):
        """Approve the role application and assign role to user"""
        from django.utils import timezone
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.review_note = note
        self.reviewed_at = timezone.now()
        self.save()

        # Add role to user
        self.user.add_role(self.role)
        self.user.save()

    def reject(self, admin_user, note=''):
        """Reject the role application"""
        from django.utils import timezone
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.review_note = note
        self.reviewed_at = timezone.now()
        self.save()

    def get_role_display(self):
        """Get human-readable role name"""
        return dict(User.SERVICE_ROLE_CHOICES).get(self.role, self.role)


class VerificationCode(models.Model):
    """4-digit verification codes for PWA signup/verification"""
    PURPOSE_CHOICES = [
        ('signup', 'Signup Verification'),
        ('login', 'Login Verification'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='signup')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'purpose', 'used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.purpose} - {self.code}"

    @classmethod
    def generate_for_user(cls, user, purpose='signup', ttl_minutes=15):
        """Create and return a new verification code for the user"""
        from random import randint
        code = f"{randint(1000, 9999)}"
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        # Optionally invalidate previous unused codes for same purpose
        cls.objects.filter(user=user, purpose=purpose, used=False).update(used=True)
        return cls.objects.create(user=user, code=code, purpose=purpose, expires_at=expires_at)

    def is_valid(self, input_code: str) -> bool:
        return (
            (not self.used) and
            self.code == input_code and
            self.expires_at > timezone.now()
        )
