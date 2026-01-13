from django.contrib import admin
from .models import (
    MedicineCategory, Pharmacy, Medicine, Prescription, Cart, CartItem,
    Order, OrderItem, OrderStatusHistory, Review, ReviewHelpful, Wishlist
)


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'status', 'is_verified', 'is_featured', 'license_number', 'created_at')
    list_filter = ('status', 'is_verified', 'is_featured', 'license_type', 'city', 'delivery_available', 'is_24_hours')
    search_fields = ('name', 'owner__username', 'owner__email', 'license_number', 'city', 'address')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('average_rating', 'total_reviews', 'created_at', 'updated_at', 'medicine_count')
    list_per_page = 25
    raw_id_fields = ('owner',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'owner', 'description', 'logo', 'image')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country', 'latitude', 'longitude')
        }),
        ('License & Registration', {
            'fields': ('license_number', 'license_type', 'license_expiry_date', 'registration_number', 'is_verified')
        }),
        ('Business Settings', {
            'fields': ('status', 'is_featured', 'opening_hours', 'is_24_hours')
        }),
        ('Delivery Settings', {
            'fields': ('delivery_available', 'minimum_order_amount', 'delivery_fee', 'free_delivery_threshold', 'estimated_delivery_time')
        }),
        ('Ratings & Stats', {
            'fields': ('average_rating', 'total_reviews', 'medicine_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_active', 'mark_as_verified', 'mark_as_featured']

    def mark_as_active(self, request, queryset):
        queryset.update(status='active')
    mark_as_active.short_description = "Mark selected pharmacies as active"

    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_as_verified.short_description = "Mark selected pharmacies as verified"

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected pharmacies as featured"


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'pharmacy', 'category', 'requires_prescription', 'price', 'discount_price', 'stock_quantity', 'is_in_stock', 'is_active', 'created_at')
    list_filter = ('requires_prescription', 'dosage_form', 'is_active', 'is_featured', 'category', 'pharmacy', 'created_at')
    search_fields = ('name', 'generic_name', 'brand_name', 'active_ingredients', 'manufacturer', 'pharmacy__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('views_count', 'created_at', 'updated_at', 'average_rating', 'review_count')
    list_per_page = 25
    raw_id_fields = ('owner', 'pharmacy')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'generic_name', 'brand_name', 'category', 'pharmacy', 'owner')
        }),
        ('Description', {
            'fields': ('description', 'usage', 'dosage', 'dosage_form')
        }),
        ('Medical Information', {
            'fields': ('active_ingredients', 'side_effects', 'warnings', 'storage_instructions')
        }),
        ('Prescription', {
            'fields': ('requires_prescription', 'prescription_type')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount_price', 'stock_quantity', 'low_stock_threshold')
        }),
        ('Product Details', {
            'fields': ('manufacturer', 'country_of_origin', 'pack_size', 'expiry_date', 'batch_number')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3')
        }),
        ('Status & Features', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_active', 'mark_as_inactive', 'mark_as_featured']

    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_as_active.short_description = "Mark selected medicines as active"

    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_as_inactive.short_description = "Mark selected medicines as inactive"

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected medicines as featured"


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('prescription_number', 'user', 'doctor_name', 'issue_date', 'expiry_date', 'status', 'is_valid', 'created_at')
    list_filter = ('status', 'issue_date', 'expiry_date', 'created_at')
    search_fields = ('prescription_number', 'user__username', 'user__email', 'doctor_name', 'doctor_license')
    readonly_fields = ('prescription_number', 'created_at', 'updated_at', 'reviewed_at', 'is_valid', 'is_expired')
    list_per_page = 25

    fieldsets = (
        ('Prescription Information', {
            'fields': ('prescription_number', 'user')
        }),
        ('Doctor Details', {
            'fields': ('doctor_name', 'doctor_license', 'hospital_clinic')
        }),
        ('Dates', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Files', {
            'fields': ('prescription_file', 'additional_file')
        }),
        ('Notes', {
            'fields': ('patient_notes', 'pharmacist_notes')
        }),
        ('Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at')
        }),
        ('Validation', {
            'fields': ('is_valid', 'is_expired', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_prescription', 'reject_prescription']

    def approve_prescription(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user)
    approve_prescription.short_description = "Approve selected prescriptions"

    def reject_prescription(self, request, queryset):
        queryset.update(status='rejected', reviewed_by=request.user)
    reject_prescription.short_description = "Reject selected prescriptions"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('unit_price', 'total_price')
    fields = ('medicine', 'quantity', 'prescription', 'unit_price', 'total_price')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'subtotal', 'total', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_items', 'subtotal', 'total', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    list_per_page = 25


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('medicine_name', 'medicine_dosage', 'medicine_form', 'unit_price', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'notes', 'changed_by', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'phone', 'tracking_number')
    readonly_fields = ('order_number', 'can_be_cancelled', 'is_delivered', 'created_at', 'updated_at')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    list_per_page = 25

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'delivery_charge', 'tax', 'total')
        }),
        ('Status', {
            'fields': ('status', 'payment_status', 'payment_method')
        }),
        ('Delivery Information', {
            'fields': ('address', 'city', 'state', 'postal_code', 'phone', 'delivery_instructions')
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'estimated_delivery_date', 'delivered_at')
        }),
        ('Notes', {
            'fields': ('order_notes', 'cancellation_reason')
        }),
        ('Metadata', {
            'fields': ('can_be_cancelled', 'is_delivered', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_confirmed', 'mark_as_delivered']

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
    mark_as_confirmed.short_description = "Mark selected orders as confirmed"

    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', delivered_at=timezone.now())
    mark_as_delivered.short_description = "Mark selected orders as delivered"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'helpful_count', 'created_at')
    list_filter = ('rating', 'is_approved', 'is_verified_purchase', 'created_at')
    search_fields = ('medicine__name', 'user__username', 'title', 'comment')
    readonly_fields = ('is_verified_purchase', 'helpful_count', 'created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Review Information', {
            'fields': ('medicine', 'user', 'order')
        }),
        ('Rating & Content', {
            'fields': ('rating', 'title', 'comment')
        }),
        ('Images', {
            'fields': ('image1', 'image2', 'image3')
        }),
        ('Moderation', {
            'fields': ('is_approved', 'is_verified_purchase', 'helpful_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_reviews', 'disapprove_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Disapprove selected reviews"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_count', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('item_count', 'created_at', 'updated_at')
    filter_horizontal = ('medicines',)
    list_per_page = 25


admin.site.register(ReviewHelpful)