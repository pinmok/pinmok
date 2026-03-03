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
import re

from django import template
from django.contrib.admin.views.main import PAGE_VAR
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from djangocmf.cmfadmin.constants import CUSTOM_SPRITE_FILE, CMF_SPRITE_FILE

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
def sprite(icon_name: str, css_class: str = '', size: int = 24) -> str:
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
def custom_sprite(icon_name: str, css_class: str = '', size: int = 24) -> str:
    sprite_path = static(CUSTOM_SPRITE_FILE)
    return _process_file(sprite_path, icon_name, css_class, size)


def _process_file(sprite_path: str, icon_name: str, css_class: str = '', size: int = 16):
    class_attr = f' class="{css_class}"' if css_class else ''
    try:
        size = int(size)
    except (ValueError, TypeError):
        size = 24

    svg_html = (
        f'<svg width="{size}" height="{size}"{class_attr} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<use href="{sprite_path}#{icon_name}"></use>'
        f'</svg>'
    )
    return mark_safe(svg_html)


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


@register.inclusion_tag('admin/pagination/paginator_previous.html')
def paginator_previous(cl):
    """
    Render the previous page button.
    Disabled when on the first page or when there is only one page.
    """
    enabled = cl.paginator.num_pages > 1 and cl.page_num > 1
    return {
        'url': cl.get_query_string({PAGE_VAR: cl.page_num - 1}) if enabled else None,
        'enabled': enabled,
    }


@register.inclusion_tag('admin/pagination/paginator_next.html')
def paginator_next(cl):
    """
    Render the next page button.
    Disabled when on the last page or when there is only one page.
    """
    enabled = cl.paginator.num_pages > 1 and cl.page_num < cl.paginator.num_pages
    return {
        'url': cl.get_query_string({PAGE_VAR: cl.page_num + 1}) if enabled else None,
        'enabled': enabled,
    }


@register.inclusion_tag('admin/includes/alert.html')
def alert(title, description=None, level='danger', variant='', dismiss=False, extra_class='', link_url=None, link_text=None):
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
    icon = sprite(categories[level_key], 'icon alert-icon')
    variant = f'alert-{variant.lower()}' if variant.lower() in {'important', 'minor'} else ''
    dismiss_class = 'alert-dismissible' if dismiss else ''
    class_attrs = ' '.join(filter(None, [f'alert-{level_key}', variant, extra_class, dismiss_class]))
    link = (link_url, link_text) if link_url and link_text else None

    return {
        'title': title,
        'description': description,
        'class_attrs': class_attrs,
        'dismiss': dismiss,
        'icon': icon,
        'link': link,
    }
