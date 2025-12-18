from django.contrib import admin
from .models import (
    Restaurant, OperatingHours, FoodCategory, MenuItem,
    AddonCategory, Addon, DeliveryZone, Cart, CartItem,
    Order, OrderItem, OrderItemAddon, Review, Wishlist, WishlistItem
)


class OperatingHoursInline(admin.TabularInline):
    model = OperatingHours
    extra = 0
    fields = ('day_of_week', 'opening_time', 'closing_time', 'is_closed')


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'status', 'is_featured', 'average_rating', 'created_at')
    list_filter = ('status', 'is_featured', 'city', 'created_at')
    search_fields = ('name', 'description', 'address', 'city', 'owner__username')
    readonly_fields = ('average_rating', 'total_reviews', 'created_at', 'updated_at')
    inlines = [OperatingHoursInline]
    list_per_page = 25


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_per_page = 20


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available', 'is_featured', 'created_at')
    list_filter = ('is_available', 'is_featured', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'category', 'created_at')
    search_fields = ('name', 'description', 'restaurant__name')
    readonly_fields = ('average_rating', 'total_reviews', 'created_at', 'updated_at')
    list_per_page = 25


@admin.register(AddonCategory)
class AddonCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_required', 'max_selection', 'display_order')
    list_filter = ('is_required',)
    search_fields = ('name',)
    list_per_page = 20


@admin.register(Addon)
class AddonAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available', 'display_order')
    list_filter = ('is_available', 'category')
    search_fields = ('name', 'category__name')
    list_per_page = 25


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'city', 'delivery_fee', 'minimum_order_amount', 'is_active', 'created_at')
    list_filter = ('is_active', 'city', 'created_at')
    search_fields = ('name', 'city', 'areas', 'restaurant__name')
    list_per_page = 25


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'restaurant', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'customer__username', 'customer__email', 'restaurant__name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    list_per_page = 25


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('customer', 'get_review_for', 'rating', 'order', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('customer__username', 'restaurant__name', 'menu_item__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    def get_review_for(self, obj):
        if obj.restaurant:
            return f"Restaurant: {obj.restaurant.name}"
        elif obj.menu_item:
            return f"Menu Item: {obj.menu_item.name}"
        return "N/A"
    get_review_for.short_description = 'Review For'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


admin.site.register(CartItem)
admin.site.register(OrderItemAddon)


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ('menu_item', 'added_at')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_item_count', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WishlistItemInline]
    list_per_page = 25

    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'menu_item', 'added_at')
    search_fields = ('wishlist__user__username', 'menu_item__name')
    readonly_fields = ('added_at',)
    list_per_page = 25
