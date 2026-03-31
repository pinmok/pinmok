#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmf_tags module

Description:
  Common template tags and filters usable across both frontend and admin interfaces.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/02/14
"""
import os
import re

from django import template
from django.conf import settings
from django.contrib.admin.views.main import PAGE_VAR
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from djangocmf.cmfadmin.constants import CUSTOM_SPRITE_FILE, CMF_SPRITE_FILE, CMF_ICON_PREFIX

register = template.Library()


@register.filter
def add_class(html, css_class: str):
    """
    Add CSS classes to any HTML element (universal version).

    This filter works on rendered HTML strings and can handle any HTML element
    including labels, inputs, selects, textareas, divs, etc. It intelligently
    appends classes to existing class attributes or creates new ones.

    Args:
        html: Rendered HTML string, SafeString, or BoundField object
        css_class: Space-separated CSS class names to add

    Returns:
        SafeString: HTML with classes added to the first opening tag

    Usage:
        {{ field.label_tag|add_class:"form-label required" }}
        {{ field.field|add_class:"form-control is-invalid" }}
        {{ some_html|add_class:"mb-3" }}
    """
    # Convert to string (BoundField.__str__() automatically renders to HTML)
    html_str = str(html)

    # Check if there's an existing class attribute
    if 'class="' in html_str:
        # Append to existing class attribute
        # Pattern matches: opening tag, then class=" and captures existing classes
        pattern = r'(<[a-zA-Z][a-zA-Z0-9]*\b[^>]*?\bclass=")([^"]*)'
        new_html = re.sub(
            pattern,
            r'\1\2 ' + css_class,  # Append new classes after existing ones
            html_str,
            count=1  # Only modify the first tag
        )
    else:
        # No existing class attribute, add a new one
        # Pattern matches: opening tag and captures the rest until >
        pattern = r'(<[a-zA-Z][a-zA-Z0-9]*\b)([^>]*>)'
        new_html = re.sub(
            pattern,
            r'\1 class="' + css_class + r'"\2',  # Insert class attribute
            html_str,
            count=1
        )

    return mark_safe(new_html)


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


@register.inclusion_tag('admin/pagination/paginator_number.html')
def paginator_number(cl, i):
    """
    Render a single page number item in the pagination list.
    Handles three states: ellipsis, current page (active), and normal page link.
    """
    if i == cl.paginator.ELLIPSIS:
        return {'ellipsis': True, 'label': cl.paginator.ELLIPSIS}
    elif i == cl.page_num:
        return {'active': True, 'label': i}
    else:
        return {'url': cl.get_query_string({PAGE_VAR: i}), 'label': i}


@register.inclusion_tag('admin/pagination/paginator_button.html')
def paginator_previous(cl):
    """
    Render the previous page button.
    Disabled when on the first page or when there is only one page.
    """
    enabled = cl.paginator.num_pages > 1 and cl.page_num > 1
    return {
        'url': cl.get_query_string({PAGE_VAR: cl.page_num - 1}) if enabled else None,
        'enabled': enabled,
        'direction': 'previous'
    }


@register.inclusion_tag('admin/pagination/paginator_button.html')
def paginator_next(cl):
    """
    Render the next page button.
    Disabled when on the last page or when there is only one page.
    """
    enabled = cl.paginator.num_pages > 1 and cl.page_num < cl.paginator.num_pages
    return {
        'url': cl.get_query_string({PAGE_VAR: cl.page_num + 1}) if enabled else None,
        'enabled': enabled,
        'direction': 'next'
    }


@register.inclusion_tag('admin/includes/alert.html')
def alert(title, level='danger', description=None, variant='', dismiss=False, extra_class='', link_url=None, link_text=None):
    """
    Render an alert component.

    Args:
        title: Alert heading text. If empty, nothing is rendered.
        description: Optional body content displayed below the heading.
        level: Alert type, one of 'danger', 'warning', 'success', 'info'. Defaults to 'danger'.
        variant: Visual variant, one of 'important', 'minor'. Leave empty for default appearance.
        dismiss: If True, renders a close button to dismiss the alert.
        link_url: Optional URL for an action link. Requires link_text to take effect.
        link_text: Optional label for the action link. Requires link_url to take effect.
        extra_class: Additional CSS classes appended to the alert element.
    """
    categories = {
        'danger': 'tabler-alert-circle',
        'warning': 'tabler-alert-triangle',
        'success': 'tabler-check',
        'info': 'tabler-info-circle'
    }

    level_key = level.lower() if level.lower() in categories else 'danger'
    alert_icon = icon(categories[level_key], 'icon alert-icon')
    variant = f'alert-{variant.lower()}' if variant.lower() in {'important', 'minor'} else ''
    dismiss_class = 'alert-dismissible' if dismiss else ''
    class_attrs = ' '.join(filter(None, [f'alert-{level_key}', variant, extra_class, dismiss_class]))
    link = (link_url, link_text) if link_url and link_text else None

    return {
        'title': title,
        'description': description,
        'class_attrs': class_attrs,
        'dismiss': dismiss,
        'icon': alert_icon,
        'link': link,
    }


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
