from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class EquipmentCategory(models.Model):
    """Categories for rental equipment (Tools, Vehicles, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Equipment Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    amenities = models.TextField(blank=True, help_text="Comma-separated amenities (e.g., Parking, WiFi, AC)")

    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.DateField(default=timezone.now)

    # Media (Google Drive)
    main_image = models.ImageField(
        upload_to='properties/',
        help_text="Main property image (Required)"
    )

    # Metadata
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Properties"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.city}"

    def get_amenities_list(self):
        """Return amenities as a list"""
        if self.amenities:
            return [a.strip() for a in self.amenities.split(',')]
        return []

    def get_main_image_url(self):
        """Get main image URL"""
        if self.main_image:
            return self.main_image.url
        return None




class Equipment(models.Model):
    """Model for rental equipment like tools, vehicles, machinery"""
    EQUIPMENT_CONDITIONS = [
        ('new', 'New'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
    ]

    RENTAL_PERIODS = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    LISTING_TYPES = [
        ('for_rent', 'For Rent'),
        ('for_sale', 'For Sale'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipment')
    category = models.ForeignKey(EquipmentCategory, on_delete=models.SET_NULL, null=True, related_name='equipment')
    name = models.CharField(max_length=200)
    description = models.TextField()
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPES, default='for_rent', help_text="Whether this equipment is for rent or for sale")
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=20, choices=EQUIPMENT_CONDITIONS, default='good')

    # Location
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)

    # Pricing
    price_per_period = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    rental_period = models.CharField(max_length=10, choices=RENTAL_PERIODS, default='daily')
    currency = models.CharField(max_length=3, default='GHS')
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Specifications
    specifications = models.TextField(blank=True, help_text="Technical specifications")

    # Availability
    is_available = models.BooleanField(default=True)
    quantity_available = models.IntegerField(default=1, validators=[MinValueValidator(0)])

    # Media (Google Drive)
    main_image = models.ImageField(upload_to='rental_items/', blank=True, null=True, help_text="Main item image")

    # Metadata
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Equipment"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.city}"

    def get_main_image_url(self):
        """Convert Google Drive share link to direct image URL"""
        if not self.main_image:
            return None

        # If already a thumbnail link, return as is
        if 'drive.google.com/thumbnail' in self.main_image:
            return self.main_image

        # Extract file ID from various Google Drive URL formats
        import re

        # Format: https://drive.google.com/file/d/FILE_ID/view
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', self.main_image)
        if match:
            file_id = match.group(1)
            # Use thumbnail API with large size for better compatibility
            return f'https://drive.google.com/thumbnail?id={file_id}&sz=w1000'

        # Format: https://drive.google.com/open?id=FILE_ID or uc?id=FILE_ID
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', self.main_image)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/thumbnail?id={file_id}&sz=w1000'

        # If no match, return original URL
        return self.main_image


class EquipmentImage(models.Model):
    """Additional images for equipment"""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='equipment_images/', blank=True, null=True, help_text="Equipment image")
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Image for {self.equipment.name}"

    def get_image_url(self):
        "Get image URL"
        if self.image:
            return self.image.url
        return None

        # Extract file ID from various Google Drive URL formats
        import re

        # Format: https://drive.google.com/file/d/FILE_ID/view
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', self.image)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/thumbnail?id={file_id}&sz=w1000'

        # Format: https://drive.google.com/open?id=FILE_ID or uc?id=FILE_ID
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', self.image)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/thumbnail?id={file_id}&sz=w1000'

        # If no match, return original URL
        return self.image


class RentalBooking(models.Model):
    """Bookings for equipment - handles rentals and purchases"""
    TRANSACTION_TYPES = [
        ('rental', 'Rental'),
        ('purchase', 'Purchase'),
    ]

    BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('online', 'Online'),
    ]

    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='rental', help_text="Whether this is a rental or purchase")
    renter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_bookings')

    # Foreign key to equipment
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='bookings')

    # Booking details
    start_date = models.DateField()
    end_date = models.DateField()
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], help_text="Number of items to rent")

    # Pricing & Payment
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    security_deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='cash', help_text="Payment method chosen by renter")

    # Status
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')

    # Additional information
    notes = models.TextField(blank=True, help_text="Special requests or notes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking: {self.equipment.name} by {self.renter.username}"


class RentalReview(models.Model):
    """Reviews for equipment"""
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_reviews')

    # Foreign key to equipment
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='reviews')

    # Review content
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.equipment.name} by {self.reviewer.username}"


class RentalMessage(models.Model):
    """Chat messages between renters and equipment owners"""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_rental_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_rental_messages')

    # Foreign key to equipment
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='messages')

    # Message content
    message = models.TextField()

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class SavedEquipment(models.Model):
    """User's saved/favorited equipment"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_equipment')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'equipment')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.equipment.name}"
