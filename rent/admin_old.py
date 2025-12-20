from django.contrib import admin
from .models import (
    EquipmentCategory,
    Equipment, EquipmentImage, RentalBooking, RentalReview, RentalMessage,
    SavedEquipment
)



class EquipmentImageInline(admin.TabularInline):
    model = EquipmentImage
    extra = 1
    fields = ('image', 'caption')


@admin.register(PropertyCategory)
class PropertyCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name', 'description')
    list_per_page = 20


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name', 'description')
    list_per_page = 20


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'listing_type', 'property_type', 'city', 'price_per_period', 'rental_period', 'is_available', 'created_at')
    list_filter = ('listing_type', 'property_type', 'rental_period', 'is_available', 'city', 'region', 'created_at')
    search_fields = ('title', 'description', 'address', 'city', 'owner__username', 'owner__email')
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    inlines = [PropertyImageInline]
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'category', 'title', 'description', 'listing_type', 'property_type')
        }),
        ('Location', {
            'fields': ('address', 'city', 'region', 'country')
        }),
        ('Property Details', {
            'fields': ('bedrooms', 'bathrooms', 'area_sqm', 'amenities')
        }),
        ('Pricing', {
            'fields': ('price_per_period', 'rental_period', 'currency', 'security_deposit')
        }),
        ('Rental Policy', {
            'fields': ('minimum_rental_years', 'pets_allowed', 'utilities_included', 'furnished', 'lease_terms')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from')
        }),
        ('Media', {
            'fields': ('main_image',)
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_available', 'mark_as_unavailable']

    def mark_as_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_as_available.short_description = "Mark selected properties as available"

    def mark_as_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_as_unavailable.short_description = "Mark selected properties as unavailable"


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'listing_type', 'category', 'city', 'condition', 'price_per_period', 'rental_period', 'quantity_available', 'is_available', 'created_at')
    list_filter = ('listing_type', 'condition', 'rental_period', 'is_available', 'city', 'region', 'created_at')
    search_fields = ('name', 'description', 'brand', 'model', 'city', 'owner__username')
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    inlines = [EquipmentImageInline]
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'category', 'name', 'description', 'listing_type', 'brand', 'model', 'condition')
        }),
        ('Location', {
            'fields': ('city', 'region')
        }),
        ('Pricing', {
            'fields': ('price_per_period', 'rental_period', 'currency', 'security_deposit')
        }),
        ('Specifications', {
            'fields': ('specifications',)
        }),
        ('Availability', {
            'fields': ('is_available', 'quantity_available')
        }),
        ('Media', {
            'fields': ('main_image',)
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_available', 'mark_as_unavailable']

    def mark_as_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_as_available.short_description = "Mark selected equipment as available"

    def mark_as_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_as_unavailable.short_description = "Mark selected equipment as unavailable"


@admin.register(RentalBooking)
class RentalBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking_type', 'renter', 'get_item_name', 'start_date', 'end_date', 'status', 'total_amount', 'created_at')
    list_filter = ('booking_type', 'status', 'start_date', 'created_at')
    search_fields = ('renter__username', 'renter__email', 'property__title', 'equipment__name')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_type', 'renter', 'property', 'equipment')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'rental_years', 'quantity')
        }),
        ('Pricing', {
            'fields': ('total_amount', 'currency', 'security_deposit_paid')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_item_name(self, obj):
        if obj.booking_type == 'property':
            return obj.property.title if obj.property else 'N/A'
        else:
            return obj.equipment.name if obj.equipment else 'N/A'
    get_item_name.short_description = 'Item'

    actions = ['confirm_booking', 'cancel_booking']

    def confirm_booking(self, request, queryset):
        queryset.update(status='confirmed')
    confirm_booking.short_description = "Confirm selected bookings"

    def cancel_booking(self, request, queryset):
        queryset.update(status='cancelled')
    cancel_booking.short_description = "Cancel selected bookings"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'property', 'room_type', 'price_per_month', 'is_available', 'created_at')
    list_filter = ('room_type', 'is_available', 'has_private_bathroom', 'created_at')
    search_fields = ('name', 'property__title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('property', 'name', 'room_type', 'description')
        }),
        ('Room Details', {
            'fields': ('size_sqm', 'has_private_bathroom', 'max_occupants')
        }),
        ('Pricing', {
            'fields': ('price_per_month',)
        }),
        ('Features', {
            'fields': ('amenities',)
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_available', 'mark_as_unavailable']

    def mark_as_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_as_available.short_description = "Mark selected rooms as available"

    def mark_as_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_as_unavailable.short_description = "Mark selected rooms as unavailable"


@admin.register(RentalReview)
class RentalReviewAdmin(admin.ModelAdmin):
    list_display = ('review_type', 'reviewer', 'get_item_name', 'rating', 'created_at')
    list_filter = ('review_type', 'rating', 'created_at')
    search_fields = ('reviewer__username', 'title', 'comment', 'property__title', 'equipment__name')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    def get_item_name(self, obj):
        if obj.review_type == 'property':
            return obj.property.title if obj.property else 'N/A'
        else:
            return obj.equipment.name if obj.equipment else 'N/A'
    get_item_name.short_description = 'Item'


@admin.register(RentalMessage)
class RentalMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'get_item_name', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'message', 'property__title', 'equipment__name')
    readonly_fields = ('created_at', 'read_at')
    list_per_page = 25

    fieldsets = (
        ('Message Information', {
            'fields': ('message_type', 'sender', 'receiver', 'property', 'equipment')
        }),
        ('Content', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_item_name(self, obj):
        if obj.message_type == 'property':
            return obj.property.title if obj.property else 'N/A'
        else:
            return obj.equipment.name if obj.equipment else 'N/A'
    get_item_name.short_description = 'Item'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        for msg in queryset:
            msg.mark_as_read()
    mark_as_read.short_description = "Mark selected messages as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
    mark_as_unread.short_description = "Mark selected messages as unread"


@admin.register(SavedProperty)
class SavedPropertyAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'property__title')
    readonly_fields = ('created_at',)
    list_per_page = 25


@admin.register(SavedEquipment)
class SavedEquipmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'equipment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'equipment__name')
    readonly_fields = ('created_at',)
    list_per_page = 25