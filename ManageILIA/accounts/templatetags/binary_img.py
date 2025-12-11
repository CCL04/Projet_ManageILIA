# accounts/templatetags/binary_img.py
import base64
from django import template

register = template.Library()

@register.filter
def bin_to_img(binary_data):
    """Convertit des données binaires en string base64 pour <img src>"""
    if binary_data:
        # On encode en base64 et on décode en string utf-8
        encoded = base64.b64encode(binary_data).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded}"
    return ""