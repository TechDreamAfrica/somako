from django.contrib import admin
from .models import Message, Conversation


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'app_type', 'sender', 'receiver', 'subject_preview', 'is_read', 'created_at')
    list_filter = ('app_type', 'is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message Info', {
            'fields': ('app_type', 'sender', 'receiver', 'subject', 'message', 'attachment')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def subject_preview(self, obj):
        return obj.subject[:50] if obj.subject else obj.message[:50] + '...'
    subject_preview.short_description = 'Preview'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'app_type', 'message_count', 'last_message_at')
    list_filter = ('app_type', 'last_message_at')
    search_fields = ('user1__username', 'user2__username')
    readonly_fields = ('created_at', 'last_message_at')
    date_hierarchy = 'last_message_at'

    def message_count(self, obj):
        return obj.get_messages().count()
    message_count.short_description = 'Messages'
