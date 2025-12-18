from django.contrib import admin
from .models import (
    VehicleCategory, DriverProfile, Vehicle, Ride, RideTracking, Rating, Payment
)


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'vehicle_type', 'base_fare', 'price_per_km', 'price_per_minute', 'max_passengers', 'is_active')
    list_filter = ('vehicle_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_per_page = 20


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'availability', 'average_rating', 'total_rides', 'created_at')
    list_filter = ('status', 'availability', 'created_at')
    search_fields = ('user__username', 'user__email', 'driver_license_number', 'national_id')
    readonly_fields = ('average_rating', 'total_rides', 'created_at', 'updated_at', 'last_location_update')
    list_per_page = 25


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('driver', 'category', 'make', 'model', 'year', 'license_plate', 'condition', 'is_active', 'is_primary')
    list_filter = ('category', 'condition', 'is_active', 'year', 'created_at')
    search_fields = ('driver__user__username', 'make', 'model', 'license_plate', 'vin_number')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('ride_id', 'passenger', 'driver', 'status', 'total_fare', 'payment_status', 'requested_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'requested_at')
    search_fields = ('ride_id', 'passenger__username', 'driver__user__username', 'pickup_address', 'dropoff_address')
    readonly_fields = ('ride_id', 'created_at', 'updated_at')
    list_per_page = 25


@admin.register(RideTracking)
class RideTrackingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'latitude', 'longitude', 'speed_kmh', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('ride__ride_id',)
    readonly_fields = ('recorded_at',)
    list_per_page = 50


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'rating_type', 'rater', 'get_rated_person', 'rating', 'created_at')
    list_filter = ('rating_type', 'rating', 'created_at')
    search_fields = ('rater__username', 'rated_user__username', 'rated_driver__user__username', 'ride__ride_id')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    def get_rated_person(self, obj):
        if obj.rating_type == 'passenger_to_driver':
            return obj.rated_driver.user.username if obj.rated_driver else 'N/A'
        else:
            return obj.rated_user.username if obj.rated_user else 'N/A'
    get_rated_person.short_description = 'Rated Person'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'ride', 'transaction_type', 'payment_method', 'amount', 'status', 'initiated_at')
    list_filter = ('transaction_type', 'payment_method', 'status', 'initiated_at')
    search_fields = ('payment_id', 'ride__ride_id', 'payer__username', 'transaction_reference')
    readonly_fields = ('payment_id', 'created_at', 'updated_at', 'completed_at', 'failed_at')
    list_per_page = 25
