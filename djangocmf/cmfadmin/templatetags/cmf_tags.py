#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmf_tags module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/4/25
"""
import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.template import RequestContext
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from djangocmf.cmfadmin.constants import CMF_ICON_PREFIX, CMF_SPRITE_FILE, CUSTOM_SPRITE_FILE
from djangocmf.cmfadmin.enums import NavType
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.templatetags.cmf_admin_tags import register


@register.filter
def truncate_filename(value, max_len=20):
    """
    Truncate a filename to a max length while preserving its extension.

    If the filename exceeds `max_len`, the base name is shortened and replaced
    with an ellipsis (…); the file extension is kept intact when possible.
    """
    name, ext = os.path.splitext(value)
    if len(value) <= max_len:
        return value
    keep = max_len - len(ext) - 1  # 1 for '…'
    return f'{name[:keep]}…{ext}' if keep > 0 else f'…{ext}'


@register.simple_tag
def icon(icon_name: str, css_class: str = '', size: int = 24) -> str:
    """
    Render an inline SVG icon from the appropriate sprite file.

    Automatically resolves the sprite source based on the icon name:
    - Names starting with 'tabler-' use the built-in CMF sprite.
    - All other names use the user-defined custom sprite file,
      configurable via the CUSTOM_SPRITE_FILE setting.

    Args:
        icon_name (str): The symbol ID of the icon in the sprite file.
        css_class (str): Additional CSS classes for the <svg> element.
        size (int): Width and height of the SVG in pixels. Defaults to 24.

    Returns:
        SafeString: An SVG element ready for template rendering.
    """
    if not icon_name:
        return mark_safe('')

    try:
        size = int(size)
    except (ValueError, TypeError):
        size = 24

    if icon_name.startswith(CMF_ICON_PREFIX):
        sprite_path = static(CMF_SPRITE_FILE)
    else:
        sprite_path = default_storage.url(getattr(settings, 'CUSTOM_SPRITE_FILE', CUSTOM_SPRITE_FILE))
    class_attr = f' class="{css_class}"' if css_class else ''

    return mark_safe(
        f'<svg width="{size}" height="{size}"{class_attr} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<use href="{sprite_path}#{icon_name}"></use>'
        f'</svg>'
    )


@register.simple_tag
def media_url(path: str) -> str:
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return path
    return default_storage.url(path)


@register.simple_tag(takes_context=True)
def navigation(context: RequestContext, nav_type: str) -> list:
    """
    Load and return the nav tree for the given nav_type.

    Usage:
        {% load cmf_tags %}
        {% navigation 'main' as nav_tree %}

    Returns a list of NavNode instances with nested children.
    """
    if nav_type not in NavType.values:
        raise ValueError(f'Invalid nav type: {nav_type}')
    request = context.get('request')
    language = getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)
    return NavService.build_tree(nav_type, language)
