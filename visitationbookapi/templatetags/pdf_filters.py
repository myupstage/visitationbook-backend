from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def divide(value, arg):
    return value // arg

@register.filter
def get_range(value):
    return range(int(value))

@register.filter
def add(value, arg):
    return value + arg

@register.filter
def subtract(value, arg):
    return value - arg

@register.filter
def slice_list(value, args):
    """
    Slice une liste avec un start et end
    Usage: {{ list|slice_list:"start,end" }}
    """
    try:
        start, end = map(int, args.split(','))
        return value[start:end]
    except (ValueError, AttributeError):
        return value