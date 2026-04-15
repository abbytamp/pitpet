from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def pet_type_label(value):
    normalized = str(value or '').strip().lower()
    if normalized in ('cat', 'kucing'):
        return 'Kucing'
    if normalized in ('dog', 'anjing'):
        return 'Anjing'
    return value or '-'


@register.filter
def is_dog(value):
    normalized = str(value or '').strip().lower()
    return normalized in ('dog', 'anjing')


@register.filter
def dog_size(weight):
    try:
        weight_value = float(weight)
    except (TypeError, ValueError):
        return '-'

    if 2 <= weight_value <= 10:
        return 'S'
    if 11 <= weight_value <= 25:
        return 'M'
    if 26 <= weight_value <= 45:
        return 'L'
    if weight_value > 45:
        return 'XL'
    return '-'


@register.filter
def rupiah(value):
    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        return '0'
    return f'{amount:,}'.replace(',', '.')
