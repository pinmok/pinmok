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
from typing import Any

from django import template
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from djangocmf.cmfadmin.constants import CMF_ICON_PREFIX, CMF_SPRITE_FILE, CUSTOM_SPRITE_FILE, CMF_CONFIG_CACHE_TTL, EXTERNAL_LINK_CACHE_KEY
from djangocmf.cmfadmin.enums import NavType, ConfigCategory
from djangocmf.cmfadmin.models import ExternalLink
from djangocmf.cmfadmin.service.config import ConfigService
from djangocmf.cmfadmin.service.navigation import NavService

register = template.Library()


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
    """
    Resolve a media file path to a full URL.

    Absolute URLs (http/https) are returned as-is.
    Relative paths are resolved via the configured default storage backend.

    Usage:
        {% media_url article.cover as url %}
        <img src="{{ url }}">
        or
        <img src="{% media_url article.cover %}">

    Args:
        path: Relative file path or absolute URL.

    Returns:
        Full URL string, or empty string if path is empty.
    """
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return path
    return default_storage.url(path)


@register.simple_tag
def site_info() -> dict:
    """
    Return site configuration as a dictionary.

    Usage:
        {% site_info as site %}
    """
    return ConfigService.get_category(ConfigCategory.SITE)


@register.simple_tag
def external_links() -> list[dict[str, Any]]:
    """
    Return a list of visible external links, ordered by sort_order.
    Results are cached to avoid repeated database queries.

    Usage:
        {% external_links as links %}
    """
    links = cache.get(EXTERNAL_LINK_CACHE_KEY)
    if links is None:
        links = list(
            ExternalLink.objects
            .filter(status=True)
            .order_by('sort_order')
            .values('title', 'url', 'image')
        )
        cache.set(EXTERNAL_LINK_CACHE_KEY, links, CMF_CONFIG_CACHE_TTL)
    return links


# ---------------------------------------------------------------------------
# Navigation tags
# ---------------------------------------------------------------------------

class NavBlockNode(template.Node):
    """Represents a single navblock definition. Not rendered directly."""

    def __init__(self, level: int | str, nodelist: template.NodeList):
        self.level = level  # int or 'default'
        self.nodelist = nodelist

    def render(self, context):
        # NavBlockNode is never rendered directly, always via NavigationNode
        return ''


class NavigationNode(template.Node):
    """
    Renders a navigation tree by recursively applying navblock templates.
    """

    def __init__(self, nav_type_var, block_nodes: list[NavBlockNode]):
        self.nav_type_var = nav_type_var
        self.block_nodes = block_nodes

    def _get_template_map(self) -> dict[int | str, template.NodeList]:
        """Build a map of {level: nodelist} from collected NavBlockNodes."""
        return {node.level: node.nodelist for node in self.block_nodes}

    def _render_nodes(self, nodes: list, level: int, template_map: dict, context) -> str:
        """Recursively render a list of NavNodes at the given level."""
        nodelist = template_map.get(level) or template_map.get('default')
        if nodelist is None:
            return ''

        result = []
        for item in nodes:
            # Render children first so {{ children }} is available
            if item.children:
                children_html = self._render_nodes(item.children, level + 1, template_map, context)
            else:
                children_html = ''

            context.push()
            context['item'] = item
            context['children'] = mark_safe(children_html)
            result.append(nodelist.render(context))
            context.pop()

        return ''.join(result)

    def render(self, context):
        nav_type = self.nav_type_var.resolve(context)

        if nav_type not in NavType.values:
            raise ValueError(f'Invalid nav_type: {nav_type}')

        request = context.get('request')
        language = getattr(request, 'LANGUAGE_CODE', None)
        tree = NavService.build_tree(nav_type, language)

        template_map = self._get_template_map()
        return self._render_nodes(tree, 1, template_map, context)


@register.tag('navigation')
def do_navigation(parser: template.base.Parser, token: template.base.Token):
    """
    Render a navigation tree with per-level templates.

    Usage:
        {% navigation 'main' %}
            {% navblock 1 %}
                <li class="nav-item">
                    <a href="{{ item.url }}">{{ item.name }}</a>
                    {% if item.children %}<ul>{{ children }}</ul>{% endif %}
                </li>
            {% endnavblock %}
            {% navblock default %}
                <li>
                    <a href="{{ item.url }}">{{ item.name }}</a>
                    {% if item.children %}<ul>{{ children }}</ul>{% endif %}
                </li>
            {% endnavblock %}
        {% endnavigation %}

    Variables available inside each navblock:
        {{ item }}          -- current NavNode (url, name, icon, target, children)
        {{ children }}      -- rendered HTML of child nodes (empty string if none)
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(f"'{bits[0]}' tag requires exactly one argument")

    nav_type_var = parser.compile_filter(bits[1])

    block_nodes = []
    while True:
        # Advance parser to next navblock or endnavigation, discarding any content in between.
        parser.parse(('navblock', 'endnavigation'))
        token = parser.next_token()
        if token.contents == 'endnavigation':
            break
        if token.contents.startswith('navblock'):
            block_nodes.append(do_navblock(parser, token))

    return NavigationNode(nav_type_var, block_nodes)


@register.tag('navblock')
def do_navblock(parser: template.base.Parser, token: template.base.Token):
    """
    Define the template for a specific navigation level.
    Use 'default' to match all levels without an explicit definition.

    Usage:
        {% navblock 1 %} ... {% endnavblock %}
        {% navblock default %} ... {% endnavblock %}
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(f"'{bits[0]}' tag requires exactly one argument (level number or 'default')")

    raw = bits[1]
    if raw == 'default':
        level = 'default'
    else:
        try:
            level = int(raw)
            if level < 1:
                raise ValueError
        except ValueError:
            raise template.TemplateSyntaxError(f"'{bits[0]}' level must be a positive integer or 'default'")

    nodelist = parser.parse(('endnavblock',))
    parser.delete_first_token()
    return NavBlockNode(level, nodelist)
