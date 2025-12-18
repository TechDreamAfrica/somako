from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, RoleApplication
from .subscription_models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from .notification_models import Notification, NotificationPreference

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'service_roles_display', 'is_verified', 'rating', 'created_at']
    list_filter = ['is_verified', 'is_staff', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'location', 'service_roles']
    ordering = ['-created_at']

    fieldsets = UserAdmin.fieldsets + (
        ('Service Roles', {'fields': ('service_roles',)}),
        ('Profile', {'fields': ('phone_number', 'location', 'profile_picture', 'bio')}),
        ('Verification', {'fields': ('is_verified', 'rating')}),
        ('Settings', {'fields': ('email_notifications', 'profile_visibility')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('service_roles', 'phone_number', 'location')}),
    )

    def service_roles_display(self, obj):
        """Display user's roles as colored badges"""
        roles = obj.get_roles_list()
        if not roles:
            return format_html('<span style="color: gray;">No roles</span>')

        badges = []
        for role in roles:
            badges.append(f'<span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-right: 4px;">{role}</span>')

        return format_html(' '.join(badges))

    service_roles_display.short_description = 'Service Roles'


@admin.register(RoleApplication)
class RoleApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'role_display', 'status_badge', 'created_at', 'reviewed_by', 'action_buttons']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['user__username', 'user__email', 'role', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Application Info', {
            'fields': ('user', 'role', 'status')
        }),
        ('Application Details', {
            'fields': ('reason', 'experience', 'document')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'review_note', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_applications', 'reject_applications']

    def role_display(self, obj):
        """Display role name"""
        return obj.get_role_display()
    role_display.short_description = 'Role'

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def action_buttons(self, obj):
        """Display quick action buttons"""
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="/admin/accounts/roleapplication/{}/change/" '
                'style="background: #10b981; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-right: 5px;">Review</a>',
                obj.pk
            )
        return '-'
    action_buttons.short_description = 'Actions'

    def approve_applications(self, request, queryset):
        """Bulk approve role applications"""
        approved_count = 0
        for application in queryset.filter(status='pending'):
            application.approve(request.user, 'Bulk approved by admin')
            approved_count += 1

        self.message_user(
            request,
            f'{approved_count} application(s) approved successfully.'
        )
    approve_applications.short_description = 'Approve selected applications'

    def reject_applications(self, request, queryset):
        """Bulk reject role applications"""
        rejected_count = 0
        for application in queryset.filter(status='pending'):
            application.reject(request.user, 'Bulk rejected by admin')
            rejected_count += 1

        self.message_user(
            request,
            f'{rejected_count} application(s) rejected.'
        )
    reject_applications.short_description = 'Reject selected applications'


admin.site.register(User, CustomUserAdmin)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'price', 'max_listings', 'is_active', 'is_popular', 'sort_order']
    list_filter = ['is_active', 'is_popular', 'name']
    search_fields = ['display_name', 'description']
    ordering = ['sort_order', 'price']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'display_name', 'description', 'price', 'currency')
        }),
        ('Features', {
            'fields': ('max_listings', 'featured_listings', 'priority_support', 'analytics_access', 'verification_badge', 'commission_rate')
        }),
        ('Visibility', {
            'fields': ('is_active', 'is_popular', 'sort_order')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_name', 'status_badge', 'start_date', 'end_date', 'days_left', 'auto_renew']
    list_filter = ['status', 'auto_renew', 'plan', 'start_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'days_remaining_display']
    ordering = ['-created_at']
    date_hierarchy = 'start_date'

    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date', 'next_billing_date', 'cancelled_at', 'days_remaining_display')
        }),
        ('Settings', {
            'fields': ('auto_renew',)
        }),
        ('Payment Info', {
            'fields': ('last_payment_date', 'last_payment_amount')
        }),
        ('Usage', {
            'fields': ('current_listings_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def plan_name(self, obj):
        return obj.plan.display_name if obj.plan else 'No Plan'
    plan_name.short_description = 'Plan'

    def status_badge(self, obj):
        colors = {
            'active': '#10b981',
            'expired': '#6b7280',
            'cancelled': '#ef4444',
            'pending': '#f59e0b'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def days_left(self, obj):
        days = obj.days_remaining()
        if days > 7:
            color = '#10b981'
        elif days > 0:
            color = '#f59e0b'
        else:
            color = '#ef4444'
        return format_html(
            '<span style="color: {}; font-weight: 700;">{} days</span>',
            color,
            days
        )
    days_left.short_description = 'Days Remaining'

    def days_remaining_display(self, obj):
        return f"{obj.days_remaining()} days"
    days_remaining_display.short_description = 'Days Remaining'


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_name', 'action_badge', 'amount', 'created_at']
    list_filter = ['action', 'created_at', 'plan']
    search_fields = ['user__username', 'user__email', 'notes']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Info', {
            'fields': ('user', 'plan', 'action', 'amount')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def plan_name(self, obj):
        return obj.plan.display_name if obj.plan else '-'
    plan_name.short_description = 'Plan'

    def action_badge(self, obj):
        colors = {
            'subscribed': '#10b981',
            'renewed': '#3b82f6',
            'upgraded': '#8b5cf6',
            'downgraded': '#f59e0b',
            'cancelled': '#ef4444',
            'expired': '#6b7280',
            'payment': '#10b981'
        }
        color = colors.get(obj.action, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type_badge', 'channel_badge', 'status_badge', 'created_at']
    list_filter = ['status', 'channel', 'notification_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'read_at', 'message_sid']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User & Type', {
            'fields': ('user', 'notification_type', 'channel', 'status')
        }),
        ('Content', {
            'fields': ('title', 'message')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'data'),
            'classes': ('collapse',)
        }),
        ('Contact Info', {
            'fields': ('phone_number', 'message_sid'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'read_at')
        }),
    )

    def notification_type_badge(self, obj):
        colors = {
            'ride': '#a855f7',
            'food': '#ef4444',
            'shop': '#3b82f6',
            'pharmacy': '#10b981',
            'rental': '#059669',
            'subscription': '#f59e0b',
            'payment': '#10b981'
        }

        # Determine color based on notification type prefix
        color = '#6b7280'
        for key, val in colors.items():
            if key in obj.notification_type:
                color = val
                break

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'

    def channel_badge(self, obj):
        colors = {
            'in_app': '#3b82f6',
            'sms': '#10b981',
            'whatsapp': '#059669',
            'email': '#f59e0b'
        }
        color = colors.get(obj.channel, '#6b7280')

        icons = {
            'in_app': '🔔',
            'sms': '📱',
            'whatsapp': '💬',
            'email': '✉️'
        }
        icon = icons.get(obj.channel, '📬')

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{} {}</span>',
            color,
            icon,
            obj.get_channel_display()
        )
    channel_badge.short_description = 'Channel'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'sent': '#10b981',
            'failed': '#ef4444',
            'read': '#6b7280'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'channels_enabled', 'app_notifications_enabled', 'created_at']
    list_filter = ['enable_in_app', 'enable_sms', 'enable_whatsapp', 'enable_email']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Channel Preferences', {
            'fields': ('enable_in_app', 'enable_sms', 'enable_whatsapp', 'enable_email')
        }),
        ('Notification Type Preferences', {
            'fields': ('ride_notifications', 'food_notifications', 'shop_notifications',
                      'pharmacy_notifications', 'rental_notifications', 'subscription_notifications')
        }),
        ('Marketing', {
            'fields': ('promotional_notifications',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def channels_enabled(self, obj):
        channels = []
        if obj.enable_in_app:
            channels.append('🔔 In-App')
        if obj.enable_sms:
            channels.append('📱 SMS')
        if obj.enable_whatsapp:
            channels.append('💬 WhatsApp')
        if obj.enable_email:
            channels.append('✉️ Email')

        return ', '.join(channels) if channels else '❌ None'
    channels_enabled.short_description = 'Enabled Channels'

    def app_notifications_enabled(self, obj):
        apps = []
        if obj.ride_notifications:
            apps.append('Ride')
        if obj.food_notifications:
            apps.append('Food')
        if obj.shop_notifications:
            apps.append('Shop')
        if obj.pharmacy_notifications:
            apps.append('Pharmacy')
        if obj.rental_notifications:
            apps.append('Rental')
        if obj.subscription_notifications:
            apps.append('Subscription')

        return ', '.join(apps) if apps else 'None'
    app_notifications_enabled.short_description = 'App Notifications'
