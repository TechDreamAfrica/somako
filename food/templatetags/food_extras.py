"""
Custom template tags and filters for Food app
"""

from django import template
import re

register = template.Library()


@register.filter
def gdrive_direct_url(url):
    """
    Convert Google Drive sharing URL to direct image URL

    From: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    To: https://drive.google.com/uc?export=view&id=FILE_ID
    """
    if not url:
        return url

    # Check if it's already a direct URL
    if 'uc?export=view' in url or 'uc?id=' in url:
        return url

    # Extract file ID from sharing URL
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/uc?export=view&id={file_id}'

    # Return original URL if pattern doesn't match
    return url


@register.filter
def gdrive_thumbnail_url(url, size='w500'):
    """
    Convert Google Drive sharing URL to thumbnail URL

    Args:
        url: Google Drive sharing URL
        size: Thumbnail size (e.g., 'w500', 'w1000')
    """
    if not url:
        return url

    # Extract file ID from sharing URL
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/thumbnail?id={file_id}&sz={size}'

    # Return original URL if pattern doesn't match
    return url


@register.filter
def lookup(d, key):
    """Template filter to look up dictionary values"""
    return d.get(key) if isinstance(d, dict) else None
