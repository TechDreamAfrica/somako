"""
Payment Admin
"""
from django.contrib import admin
from .models import Payment, PaystackWebhookLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'user', 'amount', 'currency', 'payment_method', 'status', 'source_app', 'created_at')
    list_filter = ('status', 'payment_method', 'source_app', 'created_at')
    search_fields = ('user__username', 'user__email', 'paystack_reference', 'order_id')
    readonly_fields = ('payment_id', 'paystack_reference', 'paystack_access_code', 'transaction_id', 'paid_at', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_id', 'user', 'amount', 'currency')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'status', 'source_app', 'order_id')
        }),
        ('Paystack Information', {
            'fields': ('paystack_reference', 'paystack_access_code', 'paystack_authorization_url')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'paid_at', 'gateway_response')
        }),
        ('Customer Information', {
            'fields': ('customer_email', 'customer_phone', 'description', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaystackWebhookLog)
class PaystackWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'payment', 'processed', 'created_at')
    list_filter = ('event_type', 'processed', 'created_at')
    search_fields = ('event_type', 'payment__paystack_reference')
    readonly_fields = ('event_type', 'event_data', 'payment', 'created_at')
