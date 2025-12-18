from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from decimal import Decimal
import uuid
import string
import random
import logging

logger = logging.getLogger(__name__)


class ExpressOrder(models.Model):
    """Order model that groups multiple delivery items together"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned to Driver'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Order Info
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='express_orders')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_express_orders')
    
    # Status & Timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')
    
    # Additional Info
    special_instructions = models.TextField(blank=True, help_text="Special instructions for the entire order")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Express Order"
        verbose_name_plural = "Express Orders"
    
    def __str__(self):
        return f"Order {self.order_number} - {self.sender.username}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Check if status changed for SMS notifications
        old_status = None
        if self.pk:
            try:
                old_instance = ExpressOrder.objects.get(pk=self.pk)
                old_status = old_instance.status
            except ExpressOrder.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Send SMS notifications on status change
        if old_status and old_status != self.status and self.status != 'draft':
            self.send_status_update_sms()
            self.send_sender_status_notification()
    
    def send_status_update_sms(self):
        """Send SMS notifications to recipients about status change"""
        try:
            from utils.sms_utils import send_express_order_status_update
            result = send_express_order_status_update(self, self.status)
            return result
        except ImportError:
            return [{'success': False, 'message': 'SMS service not available', 'recipient': 'System', 'phone': 'N/A'}]
        except Exception as e:
            return [{'success': False, 'message': str(e), 'recipient': 'System', 'phone': 'N/A'}]
    
    def send_sender_status_notification(self):
        """Send SMS notification to sender about status change"""
        try:
            from utils.sms_utils import send_express_sender_notification
            result = send_express_sender_notification(self, self.status)
            logger.info(f"Sender status notification result for order {self.order_number}: {result}")
            return result
        except ImportError:
            return {'success': False, 'message': 'SMS service not available'}
        except Exception as e:
            logger.error(f"Error sending sender notification for order {self.order_number}: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def generate_order_number(self):
        """Generate unique order number"""
        prefix = 'ORD'
        while True:
            number = ''.join(random.choices(string.digits, k=8))
            order_number = f"{prefix}{number}"
            if not ExpressOrder.objects.filter(order_number=order_number).exists():
                return order_number
    
    def get_recipients(self):
        """Get all unique recipients for this order"""
        recipients = []
        for item in self.items.all():
            recipient_info = {
                'name': item.recipient_name,
                'phone': item.recipient_phone
            }
            if recipient_info not in recipients:
                recipients.append(recipient_info)
        return recipients
    
    def calculate_total_cost(self):
        """Calculate total estimated cost from all items"""
        total = sum(item.estimated_cost or Decimal('0.00') for item in self.items.all())
        self.total_estimated_cost = total
        self.save(update_fields=['total_estimated_cost'])
        return total
    
    def can_assign_driver(self):
        """Check if order can be assigned to a driver"""
        return self.status == 'pending' and self.items.exists()
    
    def assign_to_driver(self, driver):
        """Assign order to a specific driver"""
        if not self.can_assign_driver():
            return False
        
        self.driver = driver
        self.status = 'assigned'
        self.assigned_at = timezone.now()
        self.save()
        
        # Update all order items
        self.items.update(status='assigned', driver=driver)
        
        # Send notification to the assigned driver
        try:
            from utils.sms_utils import send_express_driver_assignment_notification
            driver_result = send_express_driver_assignment_notification(self, driver)
            if driver_result.get('success'):
                logger.info(f"Driver notification sent successfully for order {self.order_number}")
            else:
                logger.warning(f"Driver notification failed for order {self.order_number}: {driver_result.get('message')}")
        except ImportError:
            logger.warning("SMS service not available for driver notifications")
        except Exception as e:
            logger.error(f"Error sending driver notification for order {self.order_number}: {str(e)}")
        
        return True
    
    def send_creation_sms(self):
        """Send SMS notifications to recipients when order is created"""
        try:
            from utils.sms_utils import send_express_order_notification
            result = send_express_order_notification(self)
            return result
        except ImportError:
            return [{'success': False, 'message': 'SMS service not available', 'recipient': 'System', 'phone': 'N/A'}]
        except Exception as e:
            return [{'success': False, 'message': str(e), 'recipient': 'System', 'phone': 'N/A'}]


class ExpressOrderItem(models.Model):
    """Individual delivery item within an order"""
    
    PACKAGE_TYPES = [
        ('document', 'Document'),
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('food', 'Food Items'),
        ('fragile', 'Fragile Items'),
        ('other', 'Other'),
    ]
    
    URGENCY_LEVELS = [
        ('standard', 'Standard (24-48 hours)'),
        ('express', 'Express (Same day)'),
        ('urgent', 'Urgent (2-4 hours)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned to Driver'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    # Relationships
    order = models.ForeignKey(ExpressOrder, on_delete=models.CASCADE, related_name='items')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_order_items')
    
    # Item tracking
    item_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Recipient Info
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    
    # Package Details
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, default='other')
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in kg")
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Declared value in GH₵")
    urgency = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='standard')
    
    # Pickup Address (inherited from sender, can be overridden)
    pickup_region = models.ForeignKey('DeliveryRegion', on_delete=models.PROTECT, related_name='pickup_order_items', null=True, blank=True)
    pickup_area = models.ForeignKey('DeliveryArea', on_delete=models.PROTECT, related_name='pickup_order_items', null=True, blank=True)
    pickup_address = models.TextField()
    pickup_landmark = models.CharField(max_length=200, blank=True)
    pickup_instructions = models.TextField(blank=True)
    
    # Delivery Address
    delivery_region = models.ForeignKey('DeliveryRegion', on_delete=models.PROTECT, related_name='delivery_order_items', null=True, blank=True)
    delivery_area = models.ForeignKey('DeliveryArea', on_delete=models.PROTECT, related_name='delivery_order_items', null=True, blank=True)
    delivery_address = models.TextField()
    delivery_landmark = models.CharField(max_length=200, blank=True)
    delivery_instructions = models.TextField(blank=True)
    
    # Pricing & Status
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Delivery Confirmation
    recipient_signature = models.TextField(blank=True, help_text="Base64 encoded signature image")
    signature_date = models.DateTimeField(null=True, blank=True)
    signed_by_name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Express Order Item"
        verbose_name_plural = "Express Order Items"
    
    def __str__(self):
        return f"Item {self.item_number} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.item_number:
            self.item_number = self.generate_item_number()
        
        # Check if driver is being assigned for the first time
        old_driver = None
        if self.pk:
            try:
                old_instance = ExpressOrderItem.objects.get(pk=self.pk)
                old_driver = old_instance.driver
            except ExpressOrderItem.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Create corresponding DeliveryRequest when item is assigned to driver
        if self.driver and old_driver != self.driver:
            self.create_delivery_request()
        
        # Sync status with related delivery request if it exists
        elif hasattr(self, 'delivery_request') and not hasattr(self, '_skip_sync'):
            self.sync_status_to_delivery_request()
    
    def create_delivery_request(self):
        """Create a corresponding DeliveryRequest for this order item"""
        if not self.driver:
            return None
            
        # Check if DeliveryRequest already exists for this item
        existing_request = DeliveryRequest.objects.filter(
            related_order_item=self
        ).first()
        
        if existing_request:
            return existing_request
        
        # Create new DeliveryRequest
        delivery_request = DeliveryRequest.objects.create(
            sender=self.order.sender,
            driver=self.driver,
            
            # Recipient Info
            recipient_name=self.recipient_name,
            recipient_phone=self.recipient_phone,
            
            # Package Details
            package_type=self.package_type,
            description=f"Order Item: {self.description}",
            weight=self.weight,
            value=self.value,
            urgency=self.urgency,
            
            # Pickup Address
            pickup_region=self.pickup_region,
            pickup_area=self.pickup_area,
            pickup_address=self.pickup_address,
            pickup_landmark=self.pickup_landmark,
            pickup_instructions=self.pickup_instructions,
            
            # Delivery Address
            delivery_region=self.delivery_region,
            delivery_area=self.delivery_area,
            delivery_address=self.delivery_address,
            delivery_landmark=self.delivery_landmark,
            delivery_instructions=self.delivery_instructions,
            
            # Pricing & Status
            estimated_cost=self.estimated_cost,
            final_cost=self.final_cost,
            status='assigned',
            
            # Link back to order item
            related_order_item=self
        )
        
        return delivery_request
    
    def sync_status_to_delivery_request(self):
        """Sync this order item's status to the related delivery request"""
        if not hasattr(self, 'delivery_request'):
            return
            
        delivery_request = self.delivery_request
        
        # Map ExpressOrderItem status to DeliveryRequest status
        status_mapping = {
            'pending': 'pending',
            'assigned': 'assigned',
            'picked_up': 'picked_up',
            'in_transit': 'in_transit',
            'delivered': 'delivered',
            'failed': 'failed'
        }
        
        new_status = status_mapping.get(self.status, 'pending')
        if delivery_request.status != new_status:
            # Prevent infinite loops
            delivery_request._skip_sync = True
            delivery_request.status = new_status
            
            # Also sync timing fields
            if self.pickup_time and not delivery_request.pickup_time:
                delivery_request.pickup_time = self.pickup_time
            if self.delivery_time and not delivery_request.delivery_time:
                delivery_request.delivery_time = self.delivery_time
            if self.final_cost and not delivery_request.final_cost:
                delivery_request.final_cost = self.final_cost
                
            delivery_request.save()
            delattr(delivery_request, '_skip_sync')
    
    def generate_item_number(self):
        """Generate unique item number"""
        prefix = 'ITM'
        while True:
            number = ''.join(random.choices(string.digits, k=8))
            item_number = f"{prefix}{number}"
            if not ExpressOrderItem.objects.filter(item_number=item_number).exists():
                return item_number


class DeliveryRegion(models.Model):
    """Delivery regions for package delivery"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code for the region (e.g., ACC, KSI)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Delivery Region"
        verbose_name_plural = "Delivery Regions"

    def __str__(self):
        return self.name


class DeliveryArea(models.Model):
    """Sub-areas within delivery regions"""
    region = models.ForeignKey(DeliveryRegion, on_delete=models.CASCADE, related_name='areas')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, help_text="Short code for the area")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['region__name', 'name']
        unique_together = [['region', 'name'], ['region', 'code']]
        verbose_name = "Delivery Area"
        verbose_name_plural = "Delivery Areas"

    def __str__(self):
        return f"{self.region.name} - {self.name}"


class DeliveryRequest(models.Model):
    """Package delivery request model"""
    
    PACKAGE_TYPES = [
        ('document', 'Document'),
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('food', 'Food Items'),
        ('fragile', 'Fragile Items'),
        ('other', 'Other'),
    ]
    
    URGENCY_LEVELS = [
        ('standard', 'Standard (24-48 hours)'),
        ('express', 'Express (Same day)'),
        ('urgent', 'Urgent (2-4 hours)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned to Driver'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    # Request Info
    tracking_number = models.CharField(max_length=20, unique=True, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_packages')
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    
    # Package Details
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, default='other')
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in kg")
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Declared value in GH₵")
    urgency = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='standard')
    
    # Addresses
    pickup_region = models.ForeignKey(DeliveryRegion, on_delete=models.PROTECT, related_name='pickup_deliveries', null=True, blank=True)
    pickup_area = models.ForeignKey(DeliveryArea, on_delete=models.PROTECT, related_name='pickup_deliveries', null=True, blank=True)
    pickup_address = models.TextField()
    pickup_landmark = models.CharField(max_length=200, blank=True)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    delivery_region = models.ForeignKey(DeliveryRegion, on_delete=models.PROTECT, related_name='delivery_deliveries', null=True, blank=True)
    delivery_area = models.ForeignKey(DeliveryArea, on_delete=models.PROTECT, related_name='delivery_deliveries', null=True, blank=True)
    delivery_address = models.TextField()
    delivery_landmark = models.CharField(max_length=200, blank=True)
    delivery_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Pricing & Payment
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')
    
    # Status & Assignment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_deliveries')
    
    # Link to ExpressOrderItem (if this delivery was created from an order item)
    related_order_item = models.OneToOneField('ExpressOrderItem', on_delete=models.CASCADE, null=True, blank=True, related_name='delivery_request')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)

    # Special Instructions
    pickup_instructions = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)

    # Delivery Confirmation
    recipient_signature = models.TextField(blank=True, help_text="Base64 encoded signature image")
    signature_date = models.DateTimeField(null=True, blank=True)
    signed_by_name = models.CharField(max_length=100, blank=True)
    signature_ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Delivery Request"
        verbose_name_plural = "Delivery Requests"
    
    def __str__(self):
        return f"{self.tracking_number} - {self.sender.username} to {self.recipient_name}"
    
    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
            
        # Check if delivery status changed to completed/cancelled - release driver
        if self.pk:  # Only for existing objects
            try:
                old_instance = DeliveryRequest.objects.get(pk=self.pk)
                old_status = old_instance.status
                new_status = self.status
                
                # If delivery is completed, cancelled or failed, release the driver
                if (old_status in ['assigned', 'picked_up', 'in_transit'] and 
                    new_status in ['delivered', 'cancelled', 'failed']):
                    self.release_driver()
                    
            except DeliveryRequest.DoesNotExist:
                pass  # New object, no need to check
                
        super().save(*args, **kwargs)
        
        # Sync status with related order item if this is created from an order item
        if self.related_order_item and not hasattr(self, '_skip_sync'):
            self.sync_status_to_order_item()
    
    def release_driver(self):
        """Release driver and make them available for new deliveries"""
        if self.driver:
            try:
                driver_profile = self.driver.delivery_driver_profile
                if driver_profile.availability == 'ON_DELIVERY':
                    driver_profile.availability = 'ONLINE'
                    driver_profile.save()
                    
                    # Update statistics if delivered
                    if self.status == 'delivered':
                        driver_profile.total_deliveries += 1
                        driver_profile.save()
                        
            except DeliveryDriverProfile.DoesNotExist:
                pass  # Driver doesn't have a profile
    
    def generate_tracking_number(self):
        """Generate unique tracking number"""
        prefix = 'EXP'
        while True:
            number = ''.join(random.choices(string.digits, k=8))
            tracking_number = f"{prefix}{number}"
            if not DeliveryRequest.objects.filter(tracking_number=tracking_number).exists():
                return tracking_number
    
    def can_cancel(self):
        """Check if delivery can be cancelled"""
        return self.status in ['pending', 'confirmed', 'assigned']
    
    def calculate_distance(self):
        """Calculate approximate distance between pickup and delivery"""
        if all([self.pickup_latitude, self.pickup_longitude, self.delivery_latitude, self.delivery_longitude]):
            # Simple distance calculation (you can integrate with Google Maps API)
            import math
            lat1, lon1 = float(self.pickup_latitude), float(self.pickup_longitude)
            lat2, lon2 = float(self.delivery_latitude), float(self.delivery_longitude)
            
            R = 6371  # Earth's radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c
            return round(distance, 2)
        return None

    def is_same_region(self):
        """Check if pickup and delivery are in the same region"""
        if self.pickup_region and self.delivery_region:
            return self.pickup_region.id == self.delivery_region.id
    
    def sync_status_to_order_item(self):
        """Sync this delivery's status to the related order item"""
        if not self.related_order_item:
            return
            
        # Map DeliveryRequest status to ExpressOrderItem status
        status_mapping = {
            'pending': 'pending',
            'confirmed': 'assigned',
            'assigned': 'assigned',
            'picked_up': 'picked_up',
            'in_transit': 'in_transit',
            'delivered': 'delivered',
            'cancelled': 'failed',
            'failed': 'failed'
        }
        
        new_status = status_mapping.get(self.status, 'pending')
        if self.related_order_item.status != new_status:
            # Prevent infinite loops
            self.related_order_item._skip_sync = True
            self.related_order_item.status = new_status
            
            # Also sync timing fields
            if self.pickup_time and not self.related_order_item.pickup_time:
                self.related_order_item.pickup_time = self.pickup_time
            if self.delivery_time and not self.related_order_item.delivery_time:
                self.related_order_item.delivery_time = self.delivery_time
            if self.final_cost and not self.related_order_item.final_cost:
                self.related_order_item.final_cost = self.final_cost
                
            self.related_order_item.save()
            delattr(self.related_order_item, '_skip_sync')
        return False

    def is_same_area(self):
        """Check if pickup and delivery are in the same area (deprecated - use is_same_region)"""
        # Use regional system if available
        if self.pickup_region and self.delivery_region:
            return self.is_same_region()
        
        # Fallback to address parsing for backward compatibility
        pickup_area = self.extract_area_from_address(self.pickup_address)
        delivery_area = self.extract_area_from_address(self.delivery_address)
        
        if pickup_area and delivery_area:
            return pickup_area.lower() == delivery_area.lower()
        return False

    def auto_assign_driver(self):
        """Automatically assign an available driver based on region"""
        from django.db.models import Q
        import random
        
        if self.driver or self.status not in ['pending', 'confirmed']:
            return False  # Already assigned or not ready for assignment
            
        # Get available drivers in the pickup region first, then expand to delivery region
        available_drivers = DeliveryDriverProfile.objects.filter(
            status='APPROVED',
            availability='ONLINE',
            user__delivery_driver_profile__isnull=False
        ).exclude(
            # Exclude drivers who already have active deliveries
            user__assigned_deliveries__status__in=['assigned', 'picked_up', 'in_transit']
        )
        
        # Try to find drivers who have worked in the pickup region before
        regional_drivers = available_drivers.filter(
            Q(user__assigned_deliveries__pickup_region=self.pickup_region) |
            Q(user__assigned_deliveries__delivery_region=self.pickup_region)
        ).distinct()
        
        # If no regional drivers, expand to all available drivers
        if not regional_drivers.exists():
            regional_drivers = available_drivers
            
        if not regional_drivers.exists():
            return False  # No available drivers
            
        # Randomly select a driver to ensure fair distribution
        driver_profiles = list(regional_drivers)
        selected_profile = random.choice(driver_profiles)
        
        # Assign the driver
        self.driver = selected_profile.user
        self.status = 'assigned'
        self.save()
        
        # Update driver availability
        selected_profile.availability = 'ON_DELIVERY'
        selected_profile.save()
        
        # Create status update record
        DeliveryStatusUpdate.objects.create(
            delivery=self,
            status='assigned',
            notes=f'Automatically assigned to {selected_profile.user.get_full_name()}',
            updated_by=self.sender  # System assignment
        )
        
        # Send notification to the driver
        self.notify_driver_assignment()
        
        return True
    
    def notify_driver_assignment(self):
        """Send notification to assigned driver"""
        if not self.driver:
            return
            
        # Import SMS function
        try:
            from express_pwa.views import send_delivery_sms
            
            # Get driver's phone number
            driver_phone = None
            if hasattr(self.driver, 'phone_number') and self.driver.phone_number:
                driver_phone = self.driver.phone_number
            
            # Create SMS message
            pickup_location = self.pickup_area.name if self.pickup_area else "Unknown Area"
            delivery_location = self.delivery_area.name if self.delivery_area else "Unknown Area"
            
            sms_message = (
                f"New delivery assignment! "
                f"Tracking: {self.tracking_number}. "
                f"Pickup: {pickup_location} "
                f"Delivery: {delivery_location}. "
                f"Contact sender: {self.sender.phone_number if hasattr(self.sender, 'phone_number') else 'N/A'}. "
                f"Check your dashboard for details."
            )
            
            # Send SMS if phone number is available
            if driver_phone:
                send_delivery_sms(driver_phone, sms_message)
            
        except ImportError:
            pass  # SMS service not available
            
        # Also try to create in-app notification  
        try:
            from accounts.notification_models import Notification
            
            Notification.objects.create(
                user=self.driver,
                notification_type='delivery_assigned',
                title='New Delivery Assignment',
                message=f'You have been assigned delivery {self.tracking_number}. Pickup from {self.pickup_area.name if self.pickup_area else "Unknown"} to {self.delivery_area.name if self.delivery_area else "Unknown"}.',
                reference_id=str(self.id)
            )
        except (ImportError, Exception):
            # If notification system is not available or has issues, skip
            pass

    def extract_area_from_address(self, address):
        """Extract area/neighborhood from address string"""
        if not address:
            return None
        
        # Common area identifiers in Ghanaian addresses
        area_keywords = [
            'area', 'community', 'estate', 'town', 'village', 'suburb',
            'neighborhood', 'neighbourhood', 'district', 'sector'
        ]
        
        # Split address by common separators
        parts = address.replace(',', ' ').replace('-', ' ').replace('/', ' ').split()
        
        # Look for area patterns
        for i, part in enumerate(parts):
            part_lower = part.lower()
            # Check if current word is an area keyword
            if any(keyword in part_lower for keyword in area_keywords):
                # Return the previous word + current word if available
                if i > 0:
                    return f"{parts[i-1]} {part}"
                return part
            
            # Check for numbered areas (e.g., "Area 1", "Sector 5")
            if part_lower == 'area' and i + 1 < len(parts):
                return f"{part} {parts[i+1]}"
            if part_lower == 'sector' and i + 1 < len(parts):
                return f"{part} {parts[i+1]}"
        
        # If no specific area found, use first few significant words
        significant_parts = [p for p in parts[:3] if len(p) > 2]
        if significant_parts:
            return ' '.join(significant_parts[:2])
        
        return None


class DeliveryStatusUpdate(models.Model):
    """Track status updates for deliveries"""
    
    delivery = models.ForeignKey(DeliveryRequest, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=20, choices=DeliveryRequest.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.delivery.tracking_number} - {self.get_status_display()}"


class DeliveryRating(models.Model):
    """Rating and feedback for completed deliveries"""

    delivery = models.OneToOneField(DeliveryRequest, on_delete=models.CASCADE, related_name='rating')
    rated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    driver_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    service_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.delivery.tracking_number} - {self.driver_rating}/5 stars"


class DeliveryDriverProfile(models.Model):
    """Profile for delivery drivers/riders"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]

    AVAILABILITY_CHOICES = [
        ('OFFLINE', 'Offline'),
        ('ONLINE', 'Online'),
        ('ON_DELIVERY', 'On Delivery'),
    ]

    # User & Status
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_driver_profile'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='OFFLINE')

    # License Information
    driver_license_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9-]+$',
                message='License number must contain only uppercase letters, numbers, and hyphens'
            )
        ]
    )
    license_expiry_date = models.DateField()

    # Documents
    license_document = models.FileField(upload_to='delivery_drivers/licenses/', blank=True)
    national_id = models.FileField(upload_to='delivery_drivers/national_ids/', blank=True)
    proof_of_address = models.FileField(upload_to='delivery_drivers/proof_of_address/', blank=True)
    background_check_document = models.FileField(upload_to='delivery_drivers/background_checks/', blank=True)
    profile_photo = models.ImageField(upload_to='delivery_drivers/photos/', blank=True)

    # Location Tracking
    current_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    # Statistics
    total_deliveries = models.IntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )

    # Bank Details for Payouts
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    mobile_money_provider = models.CharField(max_length=50, blank=True, help_text="e.g., MTN, Vodafone, AirtelTigo")

    # Timestamps
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery Driver Profile"
        verbose_name_plural = "Delivery Driver Profiles"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_status_display()}"

    def is_available(self):
        """Check if driver is available for new deliveries"""
        return self.status == 'APPROVED' and self.availability == 'ONLINE'

    def update_location(self, latitude, longitude):
        """Update driver's current location"""
        self.current_latitude = Decimal(str(latitude))
        self.current_longitude = Decimal(str(longitude))
        self.last_location_update = timezone.now()
        self.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])

    def update_rating(self):
        """Recalculate average rating from all delivery ratings"""
        ratings = DeliveryRating.objects.filter(
            delivery__driver=self.user
        ).values_list('driver_rating', flat=True)

        if ratings:
            total = sum(ratings)
            count = len(ratings)
            self.average_rating = Decimal(str(round(total / count, 2)))
            self.save(update_fields=['average_rating'])


class DeliveryVehicle(models.Model):
    """Vehicle used by delivery drivers"""

    VEHICLE_TYPE_CHOICES = [
        ('BIKE', 'Motorcycle/Bike'),
        ('CAR', 'Car'),
        ('VAN', 'Van'),
        ('TRUCK', 'Truck'),
    ]

    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
    ]

    # Driver & Vehicle Info
    driver = models.ForeignKey(
        DeliveryDriverProfile,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='BIKE')

    # Vehicle Details
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField(validators=[MinValueValidator(1980), MaxValueValidator(2030)])
    color = models.CharField(max_length=30)
    license_plate = models.CharField(max_length=20, unique=True)
    vin_number = models.CharField(max_length=50, blank=True, verbose_name="VIN Number")

    # Documents
    registration_document = models.FileField(upload_to='delivery_vehicles/registration/', blank=True)
    insurance_document = models.FileField(upload_to='delivery_vehicles/insurance/', blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    road_worthiness_document = models.FileField(upload_to='delivery_vehicles/road_worthiness/', blank=True)
    road_worthiness_expiry_date = models.DateField(null=True, blank=True)

    # Vehicle Photos
    photo_front = models.ImageField(upload_to='delivery_vehicles/photos/front/', blank=True)
    photo_back = models.ImageField(upload_to='delivery_vehicles/photos/back/', blank=True)
    photo_side = models.ImageField(upload_to='delivery_vehicles/photos/side/', blank=True)

    # Status
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    # Capacity
    max_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('50.00'), help_text="Maximum weight capacity in kg")
    max_dimensions = models.CharField(max_length=100, blank=True, help_text="e.g., 100x80x60 cm")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery Vehicle"
        verbose_name_plural = "Delivery Vehicles"
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.make} {self.model} ({self.license_plate})"

    def save(self, *args, **kwargs):
        """Ensure only one primary vehicle per driver"""
        if self.is_primary:
            # Set all other vehicles for this driver as non-primary
            DeliveryVehicle.objects.filter(
                driver=self.driver,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class DeliveryPayment(models.Model):
    """Payment tracking for deliveries with commission calculation"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CARD', 'Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]

    # Payment Info
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    delivery = models.OneToOneField(
        DeliveryRequest,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_payments_made'
    )
    driver = models.ForeignKey(
        DeliveryDriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_payments_received'
    )

    # Amount Breakdown
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20.00'))
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    driver_payout = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transaction_reference = models.CharField(max_length=100, blank=True)

    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    payout_date = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Delivery Payment"
        verbose_name_plural = "Delivery Payments"
        ordering = ['-initiated_at']

    def __str__(self):
        return f"Payment {self.payment_id} - {self.delivery.tracking_number}"

    def calculate_driver_payout(self):
        """Calculate commission and driver payout"""
        self.commission = (self.amount * self.commission_percentage) / Decimal('100')
        self.driver_payout = self.amount - self.commission
        self.save(update_fields=['commission', 'driver_payout'])

    def save(self, *args, **kwargs):
        """Auto-calculate commission on save"""
        if self.amount and not self.driver_payout:
            self.commission = (self.amount * self.commission_percentage) / Decimal('100')
            self.driver_payout = self.amount - self.commission
        super().save(*args, **kwargs)
