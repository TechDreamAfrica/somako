from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class PropertyCategory(models.Model):
    """Categories for rental properties (Houses, Apartments, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Property Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


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


class Property(models.Model):
    """Model for rental properties like houses, apartments, offices"""
    PROPERTY_TYPES = [
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('office', 'Office Space'),
        ('warehouse', 'Warehouse'),
        ('land', 'Land'),
        ('shop', 'Shop/Store'),
    ]

    RENTAL_PERIODS = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    LISTING_TYPES = [
        ('for_rent', 'For Rent'),
        ('for_sale', 'For Sale'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    category = models.ForeignKey(PropertyCategory, on_delete=models.SET_NULL, null=True, related_name='properties')
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPES, default='for_rent')

    # Location details
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Ghana')

    # Property details
    bedrooms = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    bathrooms = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    area_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Area in square meters")

    # Pricing
    price_per_period = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    rental_period = models.CharField(max_length=10, choices=RENTAL_PERIODS, default='monthly')
    currency = models.CharField(max_length=3, default='GHS')
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Rental Policy (for properties only)
    minimum_rental_years = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Minimum number of years property must be rented for (1-10 years)"
    )

    # Leasing Policies
    pets_allowed = models.BooleanField(default=False, help_text="Are pets allowed in this property?")
    utilities_included = models.BooleanField(default=False, help_text="Are utilities (water, electricity, etc.) included in rent?")
    furnished = models.BooleanField(default=False, help_text="Is the property furnished?")
    lease_terms = models.TextField(
        blank=True,
        help_text="Additional lease terms and conditions (e.g., maintenance responsibilities, renewal terms)"
    )

    # Features and amenities
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


class PropertyImage(models.Model):
    """Additional images for properties"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/', blank=True, null=True, help_text="Property image")
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"

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


class Room(models.Model):
    """Individual rooms within a property for rent"""
    ROOM_TYPES = [
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('master', 'Master Bedroom'),
        ('studio', 'Studio'),
        ('shared', 'Shared Room'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=100, help_text="e.g., Room 101, Master Bedroom")
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    description = models.TextField(blank=True)

    # Room details
    size_sqm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Room size in square meters")
    has_private_bathroom = models.BooleanField(default=False)
    max_occupants = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Pricing
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    # Features
    amenities = models.TextField(blank=True, help_text="Comma-separated amenities (e.g., AC, WiFi, Balcony)")

    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.DateField(default=timezone.now)

    # Media (Google Drive)
    image = models.ImageField(upload_to='property_images/', blank=True, null=True, help_text="Property image")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['property', 'name']

    def __str__(self):
        return f"{self.name} - {self.property.title}"

    def get_amenities_list(self):
        """Return amenities as a list"""
        if self.amenities:
            return [a.strip() for a in self.amenities.split(',')]
        return []

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
    """Bookings for both properties and equipment - handles rentals and purchases"""
    BOOKING_TYPES = [
        ('property', 'Property'),
        ('equipment', 'Equipment'),
    ]

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

    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPES)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='rental', help_text="Whether this is a rental or purchase")
    renter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_bookings')

    # Foreign keys to property or equipment
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='bookings')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='bookings')

    # Booking details
    start_date = models.DateField()
    end_date = models.DateField()
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], help_text="For equipment rentals")
    rental_years = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Number of years for property rental (1-10 years)"
    )

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
        if self.booking_type == 'property':
            return f"Booking: {self.property.title} by {self.renter.username}"
        else:
            return f"Booking: {self.equipment.name} by {self.renter.username}"


class RentalReview(models.Model):
    """Reviews for properties and equipment"""
    REVIEW_TYPES = [
        ('property', 'Property'),
        ('equipment', 'Equipment'),
    ]

    review_type = models.CharField(max_length=10, choices=REVIEW_TYPES)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_reviews')

    # Foreign keys
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')

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
        if self.review_type == 'property':
            return f"Review for {self.property.title} by {self.reviewer.username}"
        else:
            return f"Review for {self.equipment.name} by {self.reviewer.username}"


class RentalMessage(models.Model):
    """Chat messages between renters and property/equipment owners"""
    MESSAGE_TYPES = [
        ('property', 'Property'),
        ('equipment', 'Equipment'),
    ]

    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_rental_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_rental_messages')

    # Foreign keys to property or equipment
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')

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


class SavedProperty(models.Model):
    """User's saved/favorited properties"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_properties')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'property')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.property.title}"


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
