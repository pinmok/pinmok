#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
icons module

Description:
  Custom template tags for rendering SVG icons from sprite with flexible options.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-02
"""
from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from cmfadmin.constants import CUSTOM_SPRITE_FILE, CMF_SPRITE_FILE

register = template.Library()


@register.simple_tag
def sprite(icon_name: str, css_class: str = '', size: int = 16) -> str:
    """
    Render an inline SVG using a symbol from the sprite file.

    Args:
        icon_name (str): The ID of the icon symbol in the SVG sprite.
        size (int, optional): Width and height of the SVG in pixels. Defaults to 16.
        css_class (str, optional): Additional CSS classes for the <svg> element. Defaults to ''.

    Returns:
        django.utils.safestring.SafeString: An SVG element string ready for rendering in the template.
    """
    sprite_path = static(CMF_SPRITE_FILE)
    return _process_file(sprite_path, icon_name, css_class, size)


@register.simple_tag
def custom_sprite(icon_name: str, css_class: str = '', size: int = 16) -> str:
    sprite_path = static(CUSTOM_SPRITE_FILE)
    return _process_file(sprite_path, icon_name, css_class, size)


def _process_file(sprite_path: str, icon_name: str, css_class: str = '', size: int = 16):
    class_attr = f' class="{css_class}"' if css_class else ''
    try:
        size = int(size)
    except (ValueError, TypeError):
        size = 24

    svg_html = (
        f'<svg width="{size}" height="{size}"{class_attr}>'
        f'<use href="{sprite_path}#{icon_name}"></use>'
        f'</svg>'
    )
    return mark_safe(svg_html)
