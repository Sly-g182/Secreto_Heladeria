# gestion/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a un valor en un diccionario por su clave."""
    return dictionary.get(key)