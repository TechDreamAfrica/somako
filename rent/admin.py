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


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'icon')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


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
            'fields': ('quantity_available', 'is_available', 'views_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
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
    list_display = ('id', 'renter', 'item_name', 'transaction_type', 'start_date', 'end_date', 'total_amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'start_date', 'end_date', 'created_at')
    search_fields = ('renter__username', 'renter__email', 'equipment__name')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Booking Information', {
            'fields': ('transaction_type', 'renter', 'equipment')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'quantity')
        }),
        ('Payment', {
            'fields': ('total_amount', 'currency', 'security_deposit_paid', 'payment_method')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def item_name(self, obj):
        """Display equipment name"""
        return obj.equipment.name if obj.equipment else 'N/A'
    item_name.short_description = 'Item'


@admin.register(RentalReview)
class RentalReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'item_name', 'rating', 'title', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'equipment__name', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Review Information', {
            'fields': ('reviewer', 'equipment')
        }),
        ('Review Content', {
            'fields': ('rating', 'title', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def item_name(self, obj):
        """Display equipment name"""
        return obj.equipment.name if obj.equipment else 'N/A'
    item_name.short_description = 'Item'


@admin.register(RentalMessage)
class RentalMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'item_name', 'message_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'equipment__name', 'message')
    readonly_fields = ('created_at',)
    list_per_page = 25

    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'receiver', 'equipment')
        }),
        ('Message Content', {
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

    def item_name(self, obj):
        """Display equipment name"""
        return obj.equipment.name if obj.equipment else 'N/A'
    item_name.short_description = 'Item'

    def message_preview(self, obj):
        """Show first 50 characters of message"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'


@admin.register(SavedEquipment)
class SavedEquipmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'equipment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'equipment__name')
    readonly_fields = ('created_at',)
    list_per_page = 25

    fieldsets = (
        ('Saved Item', {
            'fields': ('user', 'equipment')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )