from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class VehicleCategory(models.Model):
    """Vehicle categories available for ride service"""
    VEHICLE_TYPES = [
        ('CAR', 'Car'),
        ('BIKE', 'Bike/Motorcycle'),
        ('VAN', 'Van'),
        ('TRUCK', 'Truck'),
        ('TRICYCLE', 'Tricycle'),
    ]

    name = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    description = models.TextField(blank=True)
    base_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base fare for this vehicle category"
    )
    price_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per kilometer"
    )
    price_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per minute (for wait time)"
    )
    max_passengers = models.PositiveIntegerField(default=4)
    is_active = models.BooleanField(default=True)
    icon = models.ImageField(upload_to='ride/vehicle_categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle Category"
        verbose_name_plural = "Vehicle Categories"
        ordering = ['vehicle_type', 'name']
        indexes = [
            models.Index(fields=['vehicle_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_vehicle_type_display()})"


class DriverProfile(models.Model):
    """Extended profile for drivers"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]

    AVAILABILITY_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('ON_RIDE', 'On Ride'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='driver_profile'
    )
    driver_license_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9-]+$',
            message='License number must contain only uppercase letters, numbers, and hyphens'
        )]
    )
    license_expiry_date = models.DateField()
    license_document = models.FileField(
        upload_to='ride/driver_documents/licenses/',
        help_text="Upload driver's license (PDF or Image)"
    )
    profile_photo = models.ImageField(
        upload_to='ride/driver_photos/',
        blank=True,
        null=True
    )

    # Verification documents
    national_id = models.FileField(
        upload_to='ride/driver_documents/ids/',
        help_text="National ID or Passport"
    )
    proof_of_address = models.FileField(
        upload_to='ride/driver_documents/addresses/',
        blank=True,
        null=True
    )
    background_check_document = models.FileField(
        upload_to='ride/driver_documents/background_checks/',
        blank=True,
        null=True
    )

    # Status and availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='OFFLINE')

    # Location tracking
    current_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Current latitude coordinate"
    )
    current_longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Current longitude coordinate"
    )
    last_location_update = models.DateTimeField(null=True, blank=True)

    # Ratings
    total_rides = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )

    # Banking information for payouts
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)

    # Timestamps
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'availability']),
            models.Index(fields=['current_latitude', 'current_longitude']),
            models.Index(fields=['average_rating']),
        ]

    def __str__(self):
        return f"Driver: {self.user.get_full_name() or self.user.username}"

    def is_available(self):
        """Check if driver is available for new rides"""
        return self.status == 'APPROVED' and self.availability == 'ONLINE'

    def update_location(self, latitude, longitude):
        """Update driver's current location"""
        self.current_latitude = Decimal(str(latitude))
        self.current_longitude = Decimal(str(longitude))
        self.last_location_update = timezone.now()
        self.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])


class Vehicle(models.Model):
    """Driver's vehicle information"""
    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
    ]

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )

    # Vehicle details
    make = models.CharField(max_length=50, help_text="e.g., Toyota, Honda")
    model = models.CharField(max_length=50, help_text="e.g., Camry, Civic")
    year = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1990),
            MaxValueValidator(2030)
        ]
    )
    color = models.CharField(max_length=30)
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9-\s]+$',
            message='License plate must contain only uppercase letters, numbers, hyphens, and spaces'
        )]
    )
    vin_number = models.CharField(
        max_length=17,
        unique=True,
        blank=True,
        null=True,
        help_text="Vehicle Identification Number"
    )

    # Vehicle documents
    registration_document = models.FileField(
        upload_to='ride/vehicle_documents/registrations/'
    )
    insurance_document = models.FileField(
        upload_to='ride/vehicle_documents/insurance/'
    )
    insurance_expiry_date = models.DateField()
    road_worthiness_certificate = models.FileField(
        upload_to='ride/vehicle_documents/roadworthiness/',
        blank=True,
        null=True
    )
    roadworthiness_expiry_date = models.DateField(null=True, blank=True)

    # Vehicle photos
    front_photo = models.ImageField(upload_to='ride/vehicle_photos/front/', blank=True, null=True)
    back_photo = models.ImageField(upload_to='ride/vehicle_photos/back/', blank=True, null=True)
    side_photo = models.ImageField(upload_to='ride/vehicle_photos/side/', blank=True, null=True)
    interior_photo = models.ImageField(upload_to='ride/vehicle_photos/interior/', blank=True, null=True)

    # Vehicle status
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary vehicle used by driver"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['driver', 'is_active', 'is_primary']),
            models.Index(fields=['license_plate']),
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model} - {self.license_plate}"

    def save(self, *args, **kwargs):
        # Ensure only one primary vehicle per driver
        if self.is_primary:
            Vehicle.objects.filter(driver=self.driver, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Ride(models.Model):
    """Ride booking and tracking"""
    STATUS_CHOICES = [
        ('REQUESTED', 'Ride Requested'),
        ('ACCEPTED', 'Driver Accepted'),
        ('DRIVER_ARRIVED', 'Driver Arrived'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED_BY_PASSENGER', 'Cancelled by Passenger'),
        ('CANCELLED_BY_DRIVER', 'Cancelled by Driver'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('WALLET', 'Wallet'),
    ]

    # Unique identifier
    ride_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Participants
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='passenger_rides'
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_rides'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rides'
    )

    # Location details
    pickup_address = models.CharField(max_length=500)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8)

    dropoff_address = models.CharField(max_length=500)
    dropoff_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    dropoff_longitude = models.DecimalField(max_digits=11, decimal_places=8)

    # Ride details
    vehicle_category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.PROTECT,
        related_name='rides'
    )
    passenger_count = models.PositiveIntegerField(default=1)
    special_requests = models.TextField(blank=True, help_text="Any special requests from passenger")

    # Status tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='REQUESTED')

    # Time tracking
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    driver_arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Completion confirmation (both driver and passenger must confirm)
    driver_completed = models.BooleanField(default=False, help_text="Driver marked ride as complete")
    passenger_completed = models.BooleanField(default=False, help_text="Passenger marked ride as complete")
    driver_completed_at = models.DateTimeField(null=True, blank=True)
    passenger_completed_at = models.DateTimeField(null=True, blank=True)

    # Distance and duration
    estimated_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimated distance in kilometers"
    )
    actual_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Actual distance traveled"
    )
    estimated_duration_minutes = models.PositiveIntegerField(
        help_text="Estimated duration in minutes"
    )
    actual_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Actual duration in minutes"
    )

    # Fare calculation
    base_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    distance_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    time_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    surge_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text="Surge pricing multiplier"
    )
    total_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='CASH'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('FAILED', 'Failed'),
            ('REFUNDED', 'Refunded'),
        ],
        default='PENDING'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ride"
        verbose_name_plural = "Rides"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['passenger', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['ride_id']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Ride {self.ride_id} - {self.status}"

    def calculate_fare(self):
        """Calculate total fare based on distance, time, and surge pricing"""
        self.base_fare = self.vehicle_category.base_fare
        self.distance_fare = self.estimated_distance_km * self.vehicle_category.price_per_km
        self.time_fare = Decimal(str(self.estimated_duration_minutes)) * self.vehicle_category.price_per_minute

        subtotal = self.base_fare + self.distance_fare + self.time_fare
        self.total_fare = subtotal * self.surge_multiplier

        return self.total_fare

    def is_active(self):
        """Check if ride is currently active"""
        return self.status in ['REQUESTED', 'ACCEPTED', 'DRIVER_ARRIVED', 'IN_PROGRESS']

    def can_be_cancelled(self):
        """Check if ride can be cancelled"""
        return self.status in ['REQUESTED', 'ACCEPTED', 'DRIVER_ARRIVED']


class RideTracking(models.Model):
    """Real-time tracking of ride location"""
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='tracking_points'
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    speed_kmh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Speed in km/h"
    )
    heading = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Direction in degrees (0-360)"
    )
    accuracy_meters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS accuracy in meters"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ride Tracking Point"
        verbose_name_plural = "Ride Tracking Points"
        ordering = ['ride', 'recorded_at']
        indexes = [
            models.Index(fields=['ride', 'recorded_at']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"Tracking for Ride {self.ride.ride_id} at {self.recorded_at}"


class Rating(models.Model):
    """Rating and review system for drivers and passengers"""
    RATING_TYPE_CHOICES = [
        ('PASSENGER_TO_DRIVER', 'Passenger Rating Driver'),
        ('DRIVER_TO_PASSENGER', 'Driver Rating Passenger'),
    ]

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rating_type = models.CharField(max_length=30, choices=RATING_TYPE_CHOICES)
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_given'
    )
    rated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_received',
        null=True,
        blank=True,
        help_text="User being rated (if rating type is driver to passenger)"
    )
    rated_driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='ratings_received',
        null=True,
        blank=True,
        help_text="Driver being rated (if rating type is passenger to driver)"
    )

    # Rating details
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review = models.TextField(blank=True, help_text="Optional written review")

    # Rating categories (optional detailed ratings)
    cleanliness_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    punctuality_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    driving_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Only for driver ratings"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rating"
        verbose_name_plural = "Ratings"
        ordering = ['-created_at']
        unique_together = [['ride', 'rating_type']]
        indexes = [
            models.Index(fields=['rated_driver', 'rating']),
            models.Index(fields=['rated_user', 'rating']),
            models.Index(fields=['rating_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.rating} stars - {self.get_rating_type_display()}"

    def save(self, *args, **kwargs):
        # Ensure proper assignment based on rating type
        if self.rating_type == 'PASSENGER_TO_DRIVER':
            self.rated_driver = self.ride.driver
            self.rated_user = None
        else:
            self.rated_user = self.ride.passenger
            self.rated_driver = None

        super().save(*args, **kwargs)

        # Update average rating
        self.update_average_rating()

    def update_average_rating(self):
        """Update the average rating for the rated entity"""
        if self.rating_type == 'PASSENGER_TO_DRIVER' and self.rated_driver:
            ratings = Rating.objects.filter(
                rating_type='PASSENGER_TO_DRIVER',
                rated_driver=self.rated_driver
            )
            avg_rating = ratings.aggregate(models.Avg('rating'))['rating__avg']
            if avg_rating:
                self.rated_driver.average_rating = Decimal(str(round(avg_rating, 2)))
                self.rated_driver.save(update_fields=['average_rating'])


class Payment(models.Model):
    """Payment tracking for rides"""
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('CANCELLED', 'Cancelled'),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('RIDE_PAYMENT', 'Ride Payment'),
        ('REFUND', 'Refund'),
        ('DRIVER_PAYOUT', 'Driver Payout'),
    ]

    # Unique identifier
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_made'
    )
    recipient = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_received'
    )

    # Payment details
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='RIDE_PAYMENT'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Platform commission amount"
    )
    driver_payout = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount paid to driver after commission"
    )

    payment_method = models.CharField(max_length=20, choices=Ride.PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')

    # Transaction details
    transaction_reference = models.CharField(max_length=100, blank=True, unique=True)
    external_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transaction ID from payment gateway"
    )
    payment_gateway_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw response from payment gateway"
    )

    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['ride', 'status']),
            models.Index(fields=['payer', 'status']),
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['status', 'initiated_at']),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status}"

    def calculate_driver_payout(self, commission_percentage=20):
        """Calculate driver payout after platform commission"""
        commission_amount = (self.amount * Decimal(str(commission_percentage))) / Decimal('100')
        self.commission = commission_amount
        self.driver_payout = self.amount - commission_amount
        return self.driver_payout
