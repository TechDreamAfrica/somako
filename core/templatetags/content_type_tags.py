"""
Template tags for content type operations and Google Drive image handling
"""
from django import template
from django.contrib.contenttypes.models import ContentType
import re

register = template.Library()


@register.filter
def get_content_type_id(obj):
    """Get the content type ID for any model instance"""
    if obj is None:
        return None
    content_type = ContentType.objects.get_for_model(obj)
    return content_type.id


@register.filter
def google_drive_image(url):
    """
    Convert Google Drive sharing link to direct image URL
    Example: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    Converts to: https://drive.google.com/uc?export=view&id=FILE_ID
    """
    if not url:
        return ''

    # Already a direct link
    if 'drive.google.com/uc?' in url:
        return url

    # Extract file ID from various Google Drive URL formats
    patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/uc?export=view&id={file_id}'

    # Return original URL if no match
    return url


@register.filter
def is_google_drive_link(url):
    """Check if URL is a Google Drive link"""
    if not url:
        return False
    return 'drive.google.com' in str(url)


@register.filter
def has_role(user, role):
    """Check if user has a specific role"""
    if hasattr(user, 'has_role'):
        return user.has_role(role)
    return False
