from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
import uuid

class MedicineCategory(models.Model):
    """Categories for organizing medicines (e.g., Pain Relief, Antibiotics, Vitamins)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Direct icon URL from any image hosting service"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Medicine Category'
        verbose_name_plural = 'Medicine Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    """Main medicine/drug model with detailed information"""

    DOSAGE_FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('suppository', 'Suppository'),
        ('powder', 'Powder'),
        ('other', 'Other'),
    ]

    # Basic Information
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    generic_name = models.CharField(max_length=200, blank=True, help_text="Generic/scientific name")
    brand_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(MedicineCategory, on_delete=models.PROTECT, related_name='medicines')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medicines', null=True)

    # Description and Usage
    description = models.TextField()
    usage = models.TextField(help_text="How to use this medicine")
    dosage = models.CharField(max_length=200, help_text="Recommended dosage (e.g., 500mg)")
    dosage_form = models.CharField(max_length=20, choices=DOSAGE_FORM_CHOICES, default='tablet')

    # Medical Information
    active_ingredients = models.TextField(help_text="List of active ingredients")
    side_effects = models.TextField(blank=True, help_text="Possible side effects")
    warnings = models.TextField(blank=True, help_text="Warnings and contraindications")
    storage_instructions = models.TextField(blank=True, help_text="Storage requirements")

    # Prescription Requirements
    requires_prescription = models.BooleanField(default=False)
    prescription_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of prescription required (e.g., regular, controlled substance)"
    )

    # Pricing and Stock
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10, help_text="Alert when stock falls below this")

    # Product Details
    manufacturer = models.CharField(max_length=200)
    country_of_origin = models.CharField(max_length=100, blank=True)
    pack_size = models.CharField(max_length=100, blank=True, help_text="Package size (e.g., 10 tablets, 100ml)")
    expiry_date = models.DateField(blank=True, null=True)
    batch_number = models.CharField(max_length=100, blank=True)

    # Images
    image = models.ImageField(
        upload_to='medicines/',
        blank=True,
        null=True,
        help_text="Main medicine image"
    )
    image_2 = models.ImageField(
        upload_to='medicines/',
        blank=True,
        null=True,
        help_text="Additional medicine image"
    )
    image_3 = models.ImageField(upload_to='medicines/', blank=True, null=True, help_text="Additional medicine image")

    # Status and Metadata
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Medicine'
        verbose_name_plural = 'Medicines'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Medicine.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.dosage_form})"

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.low_stock_threshold

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def final_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def discount_percentage(self):
        if self.discount_price and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()


class Prescription(models.Model):
    """Model for managing prescription uploads"""

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_number = models.CharField(max_length=100, unique=True, blank=True)

    # Prescription Details
    doctor_name = models.CharField(max_length=200, blank=True)
    doctor_license = models.CharField(max_length=100, blank=True)
    hospital_clinic = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    # Files
    prescription_file = models.FileField(
        upload_to='pharmacy/prescriptions/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    additional_file = models.FileField(
        upload_to='pharmacy/prescriptions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )

    # Notes
    patient_notes = models.TextField(blank=True, help_text="Additional notes from patient")
    pharmacist_notes = models.TextField(blank=True, help_text="Notes from pharmacist/reviewer")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_prescriptions'
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.prescription_number:
            self.prescription_number = f"RX-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Prescription {self.prescription_number} - {self.user.get_full_name()}"

    @property
    def is_valid(self):
        return (
            self.status == 'approved' and
            self.expiry_date >= timezone.now().date()
        )

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()


class Cart(models.Model):
    """Shopping cart for users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacy_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart - {self.user.get_full_name()}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total(self):
        # Can add delivery charges or taxes here
        return self.subtotal


class CartItem(models.Model):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Required if medicine needs prescription"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'medicine']

    def __str__(self):
        return f"{self.quantity}x {self.medicine.name}"

    @property
    def unit_price(self):
        return self.medicine.final_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def clean(self):
        from django.core.exceptions import ValidationError

        # Check if prescription is required
        if self.medicine.requires_prescription and not self.prescription:
            raise ValidationError("This medicine requires a valid prescription.")

        # Check if prescription is valid
        if self.prescription and not self.prescription.is_valid:
            raise ValidationError("The provided prescription is not valid or has expired.")

        # Check stock availability
        if self.quantity > self.medicine.stock_quantity:
            raise ValidationError(f"Only {self.medicine.stock_quantity} units available in stock.")


class Order(models.Model):
    """Pharmacy orders"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('prescription_review', 'Prescription Under Review'),
        ('processing', 'Processing'),
        ('packed', 'Packed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    # Order Information
    order_number = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacy_orders')

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Status
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')

    # Delivery Information
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_state = models.CharField(max_length=100, blank=True)
    delivery_postal_code = models.CharField(max_length=20, blank=True)
    delivery_phone = models.CharField(max_length=20)
    delivery_instructions = models.TextField(blank=True)

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery_date = models.DateField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    # Notes
    order_notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"PH-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number} - {self.user.get_full_name()}"

    @property
    def can_be_cancelled(self):
        return self.status in ['pending', 'confirmed', 'prescription_review']

    @property
    def is_delivered(self):
        return self.status == 'delivered'


class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True)

    # Store medicine details at time of order (in case product changes later)
    medicine_name = models.CharField(max_length=200)
    medicine_dosage = models.CharField(max_length=200)
    medicine_form = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.quantity}x {self.medicine_name}"

    def save(self, *args, **kwargs):
        # Store medicine details
        if not self.medicine_name:
            self.medicine_name = self.medicine.name
            self.medicine_dosage = self.medicine.dosage
            self.medicine_form = self.medicine.get_dosage_form_display()

        # Calculate prices
        if not self.unit_price:
            self.unit_price = self.medicine.final_price
        if not self.total_price:
            self.total_price = self.unit_price * self.quantity

        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=30, choices=Order.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()}"


class Review(models.Model):
    """Product reviews and ratings"""
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacy_reviews')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()

    # Images (optional)
    image_1 = models.ImageField(
        upload_to='reviews/',
        blank=True,
        null=True,
        help_text="Review image"
    )
    image_2 = models.ImageField(upload_to='medicines/', blank=True, null=True, help_text="Additional medicine image")
    image_3 = models.ImageField(upload_to='medicines/', blank=True, null=True, help_text="Additional medicine image")

    # Moderation
    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)

    # Helpfulness
    helpful_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        unique_together = ['medicine', 'user', 'order']
        indexes = [
            models.Index(fields=['medicine', 'is_approved']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.rating}-star review by {self.user.get_full_name()} for {self.medicine.name}"

    def save(self, *args, **kwargs):
        # Check if this is a verified purchase
        if self.order and self.order.items.filter(medicine=self.medicine).exists():
            self.is_verified_purchase = True
        super().save(*args, **kwargs)


class ReviewHelpful(models.Model):
    """Track users who found a review helpful"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Review Helpful Vote'
        verbose_name_plural = 'Review Helpful Votes'
        unique_together = ['review', 'user']

    def __str__(self):
        return f"{self.user.get_full_name()} found review helpful"


class Wishlist(models.Model):
    """User wishlist for medicines"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacy_wishlist')
    medicines = models.ManyToManyField(Medicine, related_name='wishlisted_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"Wishlist - {self.user.get_full_name()}"

    @property
    def item_count(self):
        return self.medicines.count()
