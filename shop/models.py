from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Category(models.Model):
    """Product categories with hierarchical support"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_full_path(self):
        """Get full category path (e.g., Electronics > Phones > Smartphones)"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)


class Product(models.Model):
    """Main product model"""
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def discounted_price(self):
        """Calculate price after discount"""
        if self.discount_percentage > 0:
            discount_amount = self.base_price * (self.discount_percentage / 100)
            return self.base_price - discount_amount
        return self.base_price

    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return None

    @property
    def total_stock(self):
        """Get total stock across all variants"""
        return self.variants.aggregate(
            total=models.Sum('stock_quantity')
        )['total'] or 0

    @property
    def is_in_stock(self):
        """Check if product has any stock available"""
        return self.total_stock > 0

    def get_primary_image(self):
        """Get the primary product image"""
        return self.images.filter(is_primary=True).first() or self.images.first()

    def get_primary_image_url(self):
        """Get the URL of the primary product image"""
        primary_image = self.get_primary_image()
        return primary_image.get_image_url() if primary_image else None


class ProductImage(models.Model):
    """Product images with ordering support"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='products/',
        help_text="Product image"
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary image per product
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)

    def get_image_url(self):
        """Get image URL"""
        if self.image:
            return self.image.url
        return None


class ProductVariant(models.Model):
    """Product variants for different sizes, colors, etc."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200, help_text="e.g., Red - Large")

    # Variant attributes
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)

    # Pricing and inventory
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Additional cost for this variant"
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    # Additional fields
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight in kg"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product Variant')
        verbose_name_plural = _('Product Variants')
        ordering = ['product', 'name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def final_price(self):
        """Calculate final price including variant adjustment"""
        return self.product.discounted_price + self.price_adjustment

    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def is_in_stock(self):
        """Check if variant is in stock"""
        return self.stock_quantity > 0


class InventoryLog(models.Model):
    """Track inventory changes for auditing"""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('damage', 'Damage/Loss'),
    ]

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='inventory_logs'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_change = models.IntegerField()
    quantity_after = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Inventory Log')
        verbose_name_plural = _('Inventory Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['variant', '-created_at']),
        ]

    def __str__(self):
        return f"{self.variant} - {self.transaction_type} ({self.quantity_change})"


class Cart(models.Model):
    """Shopping cart for users and sessions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts'
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'session_key']),
        ]

    def __str__(self):
        if self.user:
            return f"Cart - {self.user.username}"
        return f"Cart - Session {self.session_key}"

    @property
    def total_items(self):
        """Get total number of items in cart"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_price(self):
        """Calculate total price (can add tax, shipping later)"""
        return self.subtotal


class CartItem(models.Model):
    """Individual items in shopping cart"""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Cart Item')
        verbose_name_plural = _('Cart Items')
        unique_together = ['cart', 'variant']
        indexes = [
            models.Index(fields=['cart', 'variant']),
        ]

    def __str__(self):
        return f"{self.variant.product.name} ({self.quantity})"

    @property
    def unit_price(self):
        """Get current unit price"""
        return self.variant.final_price

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.unit_price * self.quantity


class Wishlist(models.Model):
    """User wishlist for products"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlists'
    )
    name = models.CharField(max_length=200, default="My Wishlist")
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Wishlist')
        verbose_name_plural = _('Wishlists')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    @property
    def total_items(self):
        """Get total number of items in wishlist"""
        return self.items.count()


class WishlistItem(models.Model):
    """Individual items in wishlist"""
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='wishlist_items'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Wishlist Item')
        verbose_name_plural = _('Wishlist Items')
        unique_together = ['wishlist', 'product', 'variant']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name}"


class Order(models.Model):
    """Customer orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
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

    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Delivery and Payment Options
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

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Shipping information
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Billing information
    billing_address = models.TextField()
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)

    # Contact information
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)

    # Additional fields
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    @property
    def total_items(self):
        """Get total number of items in order"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']

    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status == 'delivered'


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    product_name = models.CharField(max_length=300)
    variant_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        indexes = [
            models.Index(fields=['order', 'variant']),
        ]

    def __str__(self):
        return f"{self.product_name} - {self.variant_name} (x{self.quantity})"

    def save(self, *args, **kwargs):
        # Calculate total price if not set
        if not self.total_price:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_status_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Order Status History')
        verbose_name_plural = _('Order Status Histories')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Payment(models.Model):
    """Payment records for orders"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('mobile_money', 'Mobile Money'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment gateway information
    transaction_id = models.CharField(max_length=200, blank=True, db_index=True)
    gateway_response = models.JSONField(null=True, blank=True)

    # Additional fields
    notes = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id or self.id} - {self.order.order_number}"

    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'completed'


class Review(models.Model):
    """Product reviews and ratings"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="Link to purchased item for verified reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
        ordering = ['-created_at']
        unique_together = ['product', 'user', 'order_item']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.rating} stars by {self.user.username}"

    def save(self, *args, **kwargs):
        # Mark as verified purchase if linked to order item
        if self.order_item and not self.is_verified_purchase:
            self.is_verified_purchase = True
        super().save(*args, **kwargs)


class ReviewImage(models.Model):
    """Images attached to product reviews"""
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='review_images/',
        help_text="Review image"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Review Image')
        verbose_name_plural = _('Review Images')
        ordering = ['created_at']

    def __str__(self):
        return f"Image for review {self.review.id}"


class ReviewHelpful(models.Model):
    """Track users who found reviews helpful"""
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='helpful_votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='helpful_reviews'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Review Helpful Vote')
        verbose_name_plural = _('Review Helpful Votes')
        unique_together = ['review', 'user']
        indexes = [
            models.Index(fields=['review', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} found review {self.review.id} helpful"
