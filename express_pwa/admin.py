from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    DeliveryRegion, DeliveryArea, DeliveryRequest, DeliveryStatusUpdate, DeliveryRating,
    DeliveryDriverProfile, DeliveryVehicle, DeliveryPayment, ExpressOrder, ExpressOrderItem
)


@admin.register(DeliveryRegion)
class DeliveryRegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'area_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    actions = ['activate_regions', 'deactivate_regions']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def area_count(self, obj):
        count = obj.areas.filter(is_active=True).count()
        return f"{count} active areas"
    area_count.short_description = 'Active Areas'
    
    def activate_regions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} regions were successfully activated.')
    activate_regions.short_description = "Activate selected regions"
    
    def deactivate_regions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} regions were successfully deactivated.')
    deactivate_regions.short_description = "Deactivate selected regions"


@admin.register(DeliveryArea)
class DeliveryAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'region', 'is_active', 'created_at']
    list_filter = ['region', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description', 'region__name']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    actions = ['activate_areas', 'deactivate_areas']
    autocomplete_fields = ['region']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('region', 'name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('region')
        
    def activate_areas(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} areas were successfully activated.')
    activate_areas.short_description = "Activate selected areas"
    
    def deactivate_areas(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} areas were successfully deactivated.')
    deactivate_areas.short_description = "Deactivate selected areas"


@admin.register(DeliveryRequest)
class DeliveryRequestAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_number',
        'sender_name',
        'recipient_name',
        'package_type',
        'urgency',
        'status_badge',
        'driver_name',
        'estimated_cost',
        'created_at'
    ]
    list_filter = [
        'status',
        'package_type',
        'urgency',
        'payment_status',
        'pickup_region',
        'delivery_region',
        'created_at'
    ]
    search_fields = [
        'tracking_number',
        'sender__username',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'recipient_name',
        'recipient_phone',
        'pickup_address',
        'delivery_address'
    ]
    readonly_fields = [
        'tracking_number',
        'created_at',
        'updated_at',
        'pickup_time',
        'delivery_time',
        'signature_display',
        'signature_date',
        'signature_ip_address'
    ]

    fieldsets = (
        ('Tracking Information', {
            'fields': ('tracking_number', 'status', 'created_at', 'updated_at')
        }),
        ('Sender Information', {
            'fields': ('sender',)
        }),
        ('Recipient Information', {
            'fields': ('recipient_name', 'recipient_phone')
        }),
        ('Package Details', {
            'fields': (
                'package_type',
                'description',
                'weight',
                'value',
                'urgency'
            )
        }),
        ('Pickup Information', {
            'fields': (
                'pickup_region',
                'pickup_area',
                'pickup_address',
                'pickup_landmark',
                'pickup_latitude',
                'pickup_longitude',
                'pickup_instructions',
                'pickup_time'
            )
        }),
        ('Delivery Information', {
            'fields': (
                'delivery_region',
                'delivery_area',
                'delivery_address',
                'delivery_landmark',
                'delivery_latitude',
                'delivery_longitude',
                'delivery_instructions',
                'delivery_time'
            )
        }),
        ('Assignment', {
            'fields': ('driver',)
        }),
        ('Payment Information', {
            'fields': (
                'estimated_cost',
                'final_cost',
                'payment_method',
                'payment_status'
            )
        }),
        ('Delivery Confirmation', {
            'fields': (
                'signature_display',
                'signed_by_name',
                'signature_date',
                'signature_ip_address'
            ),
            'classes': ('collapse',)
        }),
    )

    def sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username
    sender_name.short_description = 'Sender'

    def driver_name(self, obj):
        if obj.driver:
            return obj.driver.get_full_name() or obj.driver.username
        return '-'
    driver_name.short_description = 'Driver'

    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'confirmed': '#10b981',
            'assigned': '#3b82f6',
            'picked_up': '#8b5cf6',
            'in_transit': '#6366f1',
            'delivered': '#059669',
            'cancelled': '#ef4444',
            'failed': '#dc2626'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def signature_display(self, obj):
        if obj.recipient_signature:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 150px; border: 1px solid #ddd; border-radius: 8px;" />',
                obj.recipient_signature
            )
        return '-'
    signature_display.short_description = 'Recipient Signature'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sender', 'driver')


@admin.register(DeliveryStatusUpdate)
class DeliveryStatusUpdateAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_tracking',
        'status_badge',
        'updated_by_name',
        'notes_preview',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'delivery__tracking_number',
        'notes',
        'updated_by__username',
        'updated_by__email'
    ]
    readonly_fields = ['created_at']

    fieldsets = (
        ('Status Update', {
            'fields': ('delivery', 'status', 'notes')
        }),
        ('Update Information', {
            'fields': (
                'updated_by',
                'location_latitude',
                'location_longitude',
                'created_at'
            )
        }),
    )

    def delivery_tracking(self, obj):
        return obj.delivery.tracking_number
    delivery_tracking.short_description = 'Tracking Number'

    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'confirmed': '#10b981',
            'assigned': '#3b82f6',
            'picked_up': '#8b5cf6',
            'in_transit': '#6366f1',
            'delivered': '#059669',
            'cancelled': '#ef4444',
            'failed': '#dc2626'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return '-'
    updated_by_name.short_description = 'Updated By'

    def notes_preview(self, obj):
        if obj.notes:
            return obj.notes[:50] + ('...' if len(obj.notes) > 50 else '')
        return '-'
    notes_preview.short_description = 'Notes'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('delivery', 'updated_by')


@admin.register(DeliveryRating)
class DeliveryRatingAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_tracking',
        'driver_rating_stars',
        'service_rating_stars',
        'rated_by_name',
        'created_at'
    ]
    list_filter = ['driver_rating', 'service_rating', 'created_at']
    search_fields = [
        'delivery__tracking_number',
        'rated_by__username',
        'rated_by__email',
        'comments'
    ]
    readonly_fields = ['created_at']

    fieldsets = (
        ('Delivery Information', {
            'fields': ('delivery',)
        }),
        ('Ratings', {
            'fields': ('driver_rating', 'service_rating', 'comments')
        }),
        ('Rating Information', {
            'fields': ('rated_by', 'created_at')
        }),
    )

    def delivery_tracking(self, obj):
        return obj.delivery.tracking_number
    delivery_tracking.short_description = 'Tracking Number'

    def driver_rating_stars(self, obj):
        stars = '★' * obj.driver_rating + '☆' * (5 - obj.driver_rating)
        return format_html(
            '<span style="color: #fbbf24; font-size: 16px;">{}</span>',
            stars
        )
    driver_rating_stars.short_description = 'Driver Rating'

    def service_rating_stars(self, obj):
        stars = '★' * obj.service_rating + '☆' * (5 - obj.service_rating)
        return format_html(
            '<span style="color: #fbbf24; font-size: 16px;">{}</span>',
            stars
        )
    service_rating_stars.short_description = 'Service Rating'

    def rated_by_name(self, obj):
        if obj.rated_by:
            return obj.rated_by.get_full_name() or obj.rated_by.username
        return '-'
    rated_by_name.short_description = 'Rated By'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('delivery', 'rated_by')


@admin.register(DeliveryDriverProfile)
class DeliveryDriverProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_name',
        'status_badge',
        'availability_badge',
        'total_deliveries',
        'average_rating_stars',
        'license_number',
        'created_at'
    ]
    list_filter = ['status', 'availability', 'created_at', 'verified_at']
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'driver_license_number',
        'mobile_money_number'
    ]
    readonly_fields = [
        'total_deliveries',
        'average_rating',
        'verified_at',
        'created_at',
        'updated_at',
        'last_location_update'
    ]
    actions = ['approve_drivers', 'reject_drivers', 'suspend_drivers', 'activate_drivers']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status', 'availability')
        }),
        ('License Information', {
            'fields': (
                'driver_license_number',
                'license_expiry_date',
                'license_document'
            )
        }),
        ('Documents', {
            'fields': (
                'national_id',
                'proof_of_address',
                'background_check_document',
                'profile_photo'
            )
        }),
        ('Location', {
            'fields': (
                'current_latitude',
                'current_longitude',
                'last_location_update'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_deliveries', 'average_rating')
        }),
        ('Payment Information', {
            'fields': (
                'bank_name',
                'account_number',
                'account_holder_name',
                'mobile_money_number',
                'mobile_money_provider'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('verified_at', 'created_at', 'updated_at')
        }),
    )

    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'Driver Name'

    def license_number(self, obj):
        return obj.driver_license_number
    license_number.short_description = 'License #'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#fbbf24',
            'APPROVED': '#10b981',
            'REJECTED': '#ef4444',
            'SUSPENDED': '#dc2626'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def availability_badge(self, obj):
        colors = {
            'OFFLINE': '#6b7280',
            'ONLINE': '#10b981',
            'ON_DELIVERY': '#3b82f6'
        }
        color = colors.get(obj.availability, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_availability_display()
        )
    availability_badge.short_description = 'Availability'

    def average_rating_stars(self, obj):
        if obj.average_rating > 0:
            stars = '★' * int(obj.average_rating) + '☆' * (5 - int(obj.average_rating))
            return format_html(
                '<span style="color: #fbbf24; font-size: 16px;">{}</span> <small>({}/5)</small>',
                stars,
                obj.average_rating
            )
        return '-'
    average_rating_stars.short_description = 'Rating'

    def approve_drivers(self, request, queryset):
        count = queryset.update(status='APPROVED', verified_at=timezone.now())
        # Add delivery_driver role to users
        for driver_profile in queryset:
            if not driver_profile.user.has_role('delivery_driver'):
                driver_profile.user.add_role('delivery_driver')
        self.message_user(request, f'{count} driver(s) approved successfully.')
    approve_drivers.short_description = 'Approve selected drivers'

    def reject_drivers(self, request, queryset):
        count = queryset.update(status='REJECTED')
        self.message_user(request, f'{count} driver(s) rejected.')
    reject_drivers.short_description = 'Reject selected drivers'

    def suspend_drivers(self, request, queryset):
        count = queryset.update(status='SUSPENDED', availability='OFFLINE')
        self.message_user(request, f'{count} driver(s) suspended.')
    suspend_drivers.short_description = 'Suspend selected drivers'

    def activate_drivers(self, request, queryset):
        count = queryset.update(status='APPROVED')
        self.message_user(request, f'{count} driver(s) activated.')
    activate_drivers.short_description = 'Activate selected drivers'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(DeliveryVehicle)
class DeliveryVehicleAdmin(admin.ModelAdmin):
    list_display = [
        'driver_name',
        'vehicle_type',
        'vehicle_info',
        'license_plate',
        'condition_badge',
        'is_primary',
        'is_active',
        'created_at'
    ]
    list_filter = ['vehicle_type', 'condition', 'is_active', 'is_primary', 'created_at']
    search_fields = [
        'driver__user__username',
        'driver__user__first_name',
        'driver__user__last_name',
        'license_plate',
        'vin_number',
        'make',
        'model'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Driver Information', {
            'fields': ('driver',)
        }),
        ('Vehicle Information', {
            'fields': (
                'vehicle_type',
                'make',
                'model',
                'year',
                'color',
                'license_plate',
                'vin_number'
            )
        }),
        ('Documents', {
            'fields': (
                'registration_document',
                'insurance_document',
                'insurance_expiry_date',
                'road_worthiness_document',
                'road_worthiness_expiry_date'
            )
        }),
        ('Photos', {
            'fields': (
                'photo_front',
                'photo_back',
                'photo_side'
            ),
            'classes': ('collapse',)
        }),
        ('Status & Capacity', {
            'fields': (
                'condition',
                'is_active',
                'is_primary',
                'max_weight_kg',
                'max_dimensions'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def driver_name(self, obj):
        return obj.driver.user.get_full_name() or obj.driver.user.username
    driver_name.short_description = 'Driver'

    def vehicle_info(self, obj):
        return f"{obj.make} {obj.model} ({obj.year})"
    vehicle_info.short_description = 'Vehicle'

    def condition_badge(self, obj):
        colors = {
            'EXCELLENT': '#10b981',
            'GOOD': '#3b82f6',
            'FAIR': '#fbbf24'
        }
        color = colors.get(obj.condition, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_condition_display()
        )
    condition_badge.short_description = 'Condition'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('driver__user')


@admin.register(DeliveryPayment)
class DeliveryPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id_short',
        'delivery_tracking',
        'sender_name',
        'driver_name',
        'amount',
        'commission',
        'driver_payout',
        'payment_method',
        'status_badge',
        'initiated_at'
    ]
    list_filter = ['status', 'payment_method', 'initiated_at', 'completed_at']
    search_fields = [
        'payment_id',
        'delivery__tracking_number',
        'sender__username',
        'sender__email',
        'transaction_reference'
    ]
    readonly_fields = [
        'payment_id',
        'commission',
        'driver_payout',
        'initiated_at',
        'completed_at'
    ]

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_id',
                'delivery',
                'sender',
                'driver',
                'status'
            )
        }),
        ('Amount Details', {
            'fields': (
                'amount',
                'commission_percentage',
                'commission',
                'driver_payout'
            )
        }),
        ('Payment Method', {
            'fields': (
                'payment_method',
                'transaction_reference'
            )
        }),
        ('Timestamps', {
            'fields': (
                'initiated_at',
                'completed_at',
                'payout_date'
            )
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def payment_id_short(self, obj):
        return str(obj.payment_id)[:8] + '...'
    payment_id_short.short_description = 'Payment ID'

    def delivery_tracking(self, obj):
        return obj.delivery.tracking_number
    delivery_tracking.short_description = 'Tracking #'

    def sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username
    sender_name.short_description = 'Sender'

    def driver_name(self, obj):
        if obj.driver:
            return obj.driver.user.get_full_name() or obj.driver.user.username
        return '-'
    driver_name.short_description = 'Driver'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#fbbf24',
            'PROCESSING': '#3b82f6',
            'COMPLETED': '#10b981',
            'FAILED': '#ef4444',
            'REFUNDED': '#8b5cf6'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('delivery', 'sender', 'driver__user')


class ExpressOrderItemInline(admin.TabularInline):
    model = ExpressOrderItem
    extra = 0
    readonly_fields = ['item_number', 'created_at', 'pickup_time', 'delivery_time']
    fields = [
        'item_number', 'recipient_name', 'recipient_phone', 'package_type',
        'description', 'weight', 'value', 'urgency', 'status', 
        'pickup_address', 'delivery_address', 'estimated_cost', 'final_cost'
    ]
    can_delete = False


@admin.register(ExpressOrder)
class ExpressOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'sender', 'driver', 'status_badge', 'item_count', 
        'total_estimated_cost', 'created_at', 'assigned_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_status', 'created_at', 'assigned_at']
    search_fields = ['order_number', 'sender__username', 'sender__email', 'driver__username']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'assigned_at', 'started_at', 'completed_at']
    list_per_page = 50
    date_hierarchy = 'created_at'
    inlines = [ExpressOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'sender', 'driver', 'status')
        }),
        ('Timing', {
            'fields': ('created_at', 'updated_at', 'assigned_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('total_estimated_cost', 'total_final_cost', 'payment_method', 'payment_status')
        }),
        ('Additional Information', {
            'fields': ('special_instructions',),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6b7280',
            'pending': '#f59e0b',
            'assigned': '#3b82f6',
            'in_progress': '#8b5cf6',
            'completed': '#10b981',
            'cancelled': '#ef4444'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sender', 'driver').prefetch_related('items')


@admin.register(ExpressOrderItem)
class ExpressOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'item_number', 'order_link', 'recipient_name', 'package_type', 
        'status_badge', 'estimated_cost', 'urgency', 'created_at'
    ]
    list_filter = ['status', 'package_type', 'urgency', 'created_at']
    search_fields = [
        'item_number', 'order__order_number', 'recipient_name', 'recipient_phone',
        'description', 'pickup_address', 'delivery_address'
    ]
    readonly_fields = [
        'item_number', 'created_at', 'pickup_time', 'delivery_time', 
        'signature_date', 'order'
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Item Information', {
            'fields': ('item_number', 'order', 'driver', 'status')
        }),
        ('Recipient Information', {
            'fields': ('recipient_name', 'recipient_phone')
        }),
        ('Package Details', {
            'fields': (
                'package_type', 'description', 'weight', 'value', 'urgency'
            )
        }),
        ('Pickup Information', {
            'fields': (
                'pickup_region', 'pickup_area', 'pickup_address',
                'pickup_landmark', 'pickup_instructions'
            )
        }),
        ('Delivery Information', {
            'fields': (
                'delivery_region', 'delivery_area', 'delivery_address',
                'delivery_landmark', 'delivery_instructions'
            )
        }),
        ('Pricing', {
            'fields': ('estimated_cost', 'final_cost')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'pickup_time', 'delivery_time'),
            'classes': ('collapse',)
        }),
        ('Delivery Confirmation', {
            'fields': ('recipient_signature', 'signature_date', 'signed_by_name'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6b7280',
            'assigned': '#3b82f6',
            'picked_up': '#f59e0b',
            'in_transit': '#8b5cf6',
            'delivered': '#10b981',
            'failed': '#ef4444'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def order_link(self, obj):
        return format_html(
            '<a href="/admin/express_pwa/expressorder/{}/change/">{}</a>',
            obj.order.id,
            obj.order.order_number
        )
    order_link.short_description = 'Order'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order', 'driver', 'pickup_region', 'delivery_region')
