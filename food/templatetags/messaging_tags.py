from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.filter
def get_content_type_id(obj):
    """Get the content type ID for any model instance"""
    if obj is None:
        return None
    content_type = ContentType.objects.get_for_model(obj)
    return content_type.id
