"""
Generic messaging models for cross-app communication
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Message(models.Model):
    """
    Generic message model that can be used across all apps (food, shop, ride, pharmacy, rent)
    Uses ContentTypes to reference any model (Restaurant, Product, Ride, etc.)
    """
    APP_TYPES = [
        ('food', 'Food'),
        ('shop', 'Shop'),
        ('ride', 'Ride'),
        ('pharmacy', 'Pharmacy'),
        ('rent', 'Rent'),
    ]

    # App context
    app_type = models.CharField(max_length=20, choices=APP_TYPES)

    # Users
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    # Generic foreign key to link to any model (Order, Restaurant, Property, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Message content
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()

    # Attachments (optional)
    attachment = models.FileField(upload_to='messages/attachments/', blank=True, null=True)

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'app_type']),
            models.Index(fields=['receiver', 'is_read']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.app_type.title()} message from {self.sender.username} to {self.receiver.username}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def get_related_object_name(self):
        """Get a display name for the related object"""
        if hasattr(self.content_object, 'name'):
            return self.content_object.name
        elif hasattr(self.content_object, 'title'):
            return self.content_object.title
        elif hasattr(self.content_object, 'order_number'):
            return f"Order #{self.content_object.order_number}"
        elif hasattr(self.content_object, 'ride_id'):
            return f"Ride #{self.content_object.ride_id}"
        return f"{self.content_type.model.title()} #{self.object_id}"


class Conversation(models.Model):
    """
    Represents a conversation thread between two users about a specific object
    """
    # Participants
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_user1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_user2'
    )

    # App context
    app_type = models.CharField(max_length=20, choices=Message.APP_TYPES)

    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Metadata
    last_message_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at']
        unique_together = ('user1', 'user2', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['user1', 'app_type']),
            models.Index(fields=['user2', 'app_type']),
            models.Index(fields=['-last_message_at']),
        ]

    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"

    def get_messages(self):
        """Get all messages in this conversation"""
        return Message.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
            sender__in=[self.user1, self.user2],
            receiver__in=[self.user1, self.user2]
        ).order_by('created_at')

    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.get_messages().filter(receiver=user, is_read=False).count()

    def get_other_user(self, user):
        """Get the other participant in the conversation"""
        return self.user2 if user == self.user1 else self.user1
