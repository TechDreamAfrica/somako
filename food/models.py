from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal

class Restaurant(models.Model):
    """Restaurant model for managing food establishments"""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='restaurants',
        help_text='Restaurant owner/manager'
    )
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to='restaurants/logos/',
        blank=True,
        null=True,
        help_text="Restaurant logo image"
    )
    image = models.ImageField(
        upload_to='restaurants/images/',
        blank=True,
        null=True,
        help_text="Main restaurant image"
    )

    # Contact Information
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    email = models.EmailField()

    # Location Information
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='Latitude coordinate for map location'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='Longitude coordinate for map location'
    )

    # Business Information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    delivery_time = models.PositiveIntegerField(
        default=30,
        help_text='Average delivery time in minutes'
    )
    opening_hours = models.TextField(
        blank=True,
        help_text='Opening hours text (e.g., "Mon-Fri: 9AM-10PM, Sat-Sun: 10AM-11PM")'
    )
    cuisine_type = models.CharField(
        max_length=100,
        blank=True,
        help_text='Type of cuisine (e.g., Italian, Chinese, Mexican)'
    )

    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )
    total_reviews = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-average_rating', 'name']
        indexes = [
            models.Index(fields=['status', '-is_featured']),
            models.Index(fields=['city', 'status']),
        ]

    def __str__(self):
        return self.name

    def get_logo_url(self):
        """Get logo URL"""
        if self.logo:
            return self.logo.url
        return None

    def get_image_url(self):
        """Get image URL"""
        if self.image:
            return self.image.url
        return None

    def is_open_now(self):
        """Check if restaurant is currently open"""
        current_time = timezone.localtime().time()
        current_day = timezone.localtime().weekday()

        operating_hours = self.operating_hours.filter(
            day_of_week=current_day,
            is_closed=False
        )

        for hours in operating_hours:
            if hours.opening_time <= current_time <= hours.closing_time:
                return True
        return False


class OperatingHours(models.Model):
    """Restaurant operating hours by day of week"""

    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='operating_hours'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_closed = models.BooleanField(default=False, help_text='Restaurant closed on this day')

    class Meta:
        ordering = ['day_of_week', 'opening_time']
        unique_together = ['restaurant', 'day_of_week', 'opening_time']
        verbose_name = 'Operating Hours'
        verbose_name_plural = 'Operating Hours'

    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK)[self.day_of_week]
        if self.is_closed:
            return f"{self.restaurant.name} - {day_name}: Closed"
        return f"{self.restaurant.name} - {day_name}: {self.opening_time} - {self.closing_time}"


class FoodCategory(models.Model):
    """Categories for organizing menu items"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Direct icon URL from any image hosting service"
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Food Category'
        verbose_name_plural = 'Food Categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """Menu items/dishes offered by restaurants"""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='menu_items'
    )
    category = models.ForeignKey(
        FoodCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='menu_items'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='menu_items/',
        blank=True,
        null=True,
        help_text="Menu item image (supports both file uploads and URLs)"
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    discounted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Availability
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)

    # Additional Info
    preparation_time = models.PositiveIntegerField(
        default=15,
        help_text='Preparation time in minutes'
    )
    calories = models.PositiveIntegerField(blank=True, null=True)
    serving_size = models.CharField(max_length=50, blank=True, help_text='e.g., 1 plate, 2 pieces')

    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )
    total_reviews = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-average_rating', 'name']
        unique_together = ['restaurant', 'slug']
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
            models.Index(fields=['category', 'is_available']),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def get_display_price(self):
        """Return the price to display (discounted if available)"""
        return self.discounted_price if self.discounted_price else self.price

    def has_discount(self):
        """Check if item has a discount"""
        return self.discounted_price is not None and self.discounted_price < self.price

    def get_image_url(self):
        """Get image URL"""
        if self.image:
            # First, get the raw name/value of the image field
            try:
                image_name = str(self.image.name) if hasattr(self.image, 'name') else str(self.image)
            except:
                image_name = str(self.image)
            
            # If it's a GitHub URL or any external URL, return it directly
            if image_name.startswith(('http://', 'https://')):
                return image_name
            
            # If it's a regular file path, try to get the URL
            if image_name and not image_name.startswith('http'):
                try:
                    return self.image.url
                except (ValueError, OSError, AttributeError):
                    # If URL generation fails, check if it's actually a URL string
                    raw_value = str(self.image)
                    if raw_value.startswith(('http://', 'https://')):
                        return raw_value
                    return None
                    
        return None


class AddonCategory(models.Model):
    """Categories for menu item addons (e.g., Extras, Sides, Drinks)"""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(
        default=False,
        help_text='Customer must select at least one addon from this category'
    )
    max_selection = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of addons customer can select from this category'
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Addon Category'
        verbose_name_plural = 'Addon Categories'

    def __str__(self):
        return self.name


class Addon(models.Model):
    """Addons/customizations for menu items"""

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    category = models.ForeignKey(
        AddonCategory,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['category', 'display_order', 'name']

    def __str__(self):
        return f"{self.name} (+{self.price})"


class Cart(models.Model):
    """Shopping cart for food orders"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='food_cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'

    def __str__(self):
        return f"Cart for {self.user.get_full_name() or self.user.username}"

    def get_total(self):
        """Calculate total cart amount"""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Individual items in shopping cart"""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    special_instructions = models.TextField(blank=True)
    addons = models.ManyToManyField(
        Addon,
        blank=True,
        related_name='cart_items'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['cart', 'menu_item']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    def get_item_price(self):
        """Get price for single item including addons"""
        base_price = self.menu_item.get_display_price()
        addons_price = sum(addon.price for addon in self.addons.all())
        return base_price + addons_price

    def get_subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.get_item_price() * self.quantity

    def get_total_price(self):
        """Calculate total price for this cart item (alias for get_subtotal)"""
        return self.get_subtotal()


class DeliveryZone(models.Model):
    """Delivery zones and associated fees"""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='delivery_zones',
        blank=True,
        null=True,
        help_text='Leave blank for general zones'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Geographic coverage
    city = models.CharField(max_length=100)
    areas = models.TextField(help_text='Comma-separated list of areas covered')

    # Delivery fees
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Delivery times
    estimated_delivery_time = models.PositiveIntegerField(
        default=30,
        help_text='Estimated delivery time in minutes'
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['city', 'name']
        indexes = [
            models.Index(fields=['city', 'is_active']),
        ]

    def __str__(self):
        if self.restaurant:
            return f"{self.restaurant.name} - {self.name}"
        return self.name


class Order(models.Model):
    """Food orders placed by customers"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('picked_up', 'Picked Up'),
        ('on_the_way', 'On the Way'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Pick Up Point'),
        ('door_delivery', 'Door Delivery'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash_on_delivery', 'Cash on Delivery'),
        ('online_payment', 'Online Payment'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Order Information
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='food_orders'
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='door_delivery'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='online_payment'
    )
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Delivery Information
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    delivery_address = models.TextField(blank=True)
    delivery_city = models.CharField(max_length=100)
    delivery_phone = models.CharField(max_length=20)
    delivery_instructions = models.TextField(blank=True)

    # Delivery tracking
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='food_deliveries'
    )
    estimated_delivery_time = models.DateTimeField(blank=True, null=True)
    actual_delivery_time = models.DateTimeField(blank=True, null=True)

    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Additional Information
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']

    def can_review(self):
        """Check if order can be reviewed"""
        return self.status == 'delivered' and not hasattr(self, 'review')


class OrderItem(models.Model):
    """Individual items in an order"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    special_instructions = models.TextField(blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    def get_subtotal(self):
        """Calculate subtotal for this order item"""
        addons_price = sum(item.addon_price for item in self.addons.all())
        return (self.price + addons_price) * self.quantity


class OrderItemAddon(models.Model):
    """Addons selected for order items"""

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    addon_name = models.CharField(max_length=100)
    addon_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    def __str__(self):
        return f"{self.addon_name} (+{self.addon_price})"


class Review(models.Model):
    """Reviews and ratings for restaurants and menu items"""

    REVIEW_TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('menu_item', 'Menu Item'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='food_reviews'
    )
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES)

    # Related objects
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )

    # Review content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)

    # Additional ratings (for restaurant reviews)
    food_quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    delivery_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    service_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )

    # Status
    is_verified = models.BooleanField(default=True, help_text='Review from verified purchase')
    is_approved = models.BooleanField(default=True)

    # Response from restaurant
    restaurant_response = models.TextField(blank=True)
    response_date = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', '-created_at']),
            models.Index(fields=['menu_item', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]

    def __str__(self):
        target = self.restaurant or self.menu_item
        return f"Review by {self.customer.get_full_name() or self.customer.username} - {target}"

    def save(self, *args, **kwargs):
        """Update average ratings when review is saved"""
        self.pk is None
        super().save(*args, **kwargs)

        # Update restaurant or menu item average ratings
        if self.restaurant:
            self.restaurant.average_rating = self.restaurant.reviews.aggregate(
                models.Avg('rating')
            )['rating__avg'] or 0
            self.restaurant.total_reviews = self.restaurant.reviews.count()
            self.restaurant.save(update_fields=['average_rating', 'total_reviews'])

        if self.menu_item:
            self.menu_item.average_rating = self.menu_item.reviews.aggregate(
                models.Avg('rating')
            )['rating__avg'] or 0
            self.menu_item.total_reviews = self.menu_item.reviews.count()
            self.menu_item.save(update_fields=['average_rating', 'total_reviews'])


class Wishlist(models.Model):
    """User wishlist for favorite menu items"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='food_wishlist'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Food Wishlist'
        verbose_name_plural = 'Food Wishlists'

    def __str__(self):
        return f"Wishlist for {self.user.get_full_name() or self.user.username}"

    def get_item_count(self):
        """Get total number of items in wishlist"""
        return self.items.count()


class WishlistItem(models.Model):
    """Individual items in wishlist"""

    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['wishlist', 'menu_item']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.menu_item.name} in {self.wishlist.user.username}'s wishlist"
