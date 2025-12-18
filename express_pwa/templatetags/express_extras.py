from django import template

register = template.Library()

@register.filter
def lookup(d, key):
    """Template filter to look up dictionary values"""
    return d.get(key) if isinstance(d, dict) else None