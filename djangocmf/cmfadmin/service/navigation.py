#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
navigation module

Description:
  Provides services for building and managing hierarchical navigation menus.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-06
"""
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from djangocmf.cmfadmin.enums import TargetChoices
from djangocmf.cmfadmin.models import Nav, NavTranslation
from djangocmf.core.constants import DEFAULT_SORT_ORDER
from djangocmf.core.libs.tree import TreeNode

CACHE_TIMEOUT = 86400  # 24 hours
CACHE_KEY_PREFIX = "nav_"


def _cache_key(nav_type: str, language: str) -> str:
    return f'{CACHE_KEY_PREFIX}_{nav_type}_{language}'


@dataclass(kw_only=True)
class NavNode(TreeNode['NavNode']):
    name: str
    url: str = ''
    icon: str = ''
    target: TargetChoices = TargetChoices.SELF
    sort_order: int = DEFAULT_SORT_ORDER
    is_visible: bool = True
    level: int = 0

    def __repr__(self):
        return f"<NavNode id={self.id} name={self.name} level={self.level}>"


class NavService:
    @classmethod
    def _load_nodes(cls, nav_type: str, language: str) -> list[NavNode]:
        """Fetch nav items from database and convert to NavNode instances."""
        items = (
            Nav.objects
            .filter(nav_type=nav_type, is_visible=True)
            .prefetch_related('translations')
            .values(
                "id", "parent_id", "url", "icon",
                "target", "sort_order", "is_visible"
            )
        )
        # Build a name lookup from translations
        translation_map = {
            t.nav_id: t.name
            for t in NavTranslation.objects.filter(
                nav__nav_type=nav_type,
                language=language,
            )
        }
        nodes = []
        for item in items:
            item['name'] = translation_map.get(item['id'], '')
            nodes.append(NavNode(**item))
        return nodes

    @classmethod
    def get_items(cls, nav_type: str, language: str | None = None, exclude_id: int | None = None) -> list[tuple[NavNode, str]]:
        """
        Retrieve nav items and flatten in DFS pre-order with indented labels.

        Args:
            nav_type: NavType value string (e.g. 'main', 'footer').
            language: Language code; falls back to default if not provided.
            exclude_id: If provided, exclude the node with this id from the result.
                    Used to prevent a node from appearing as its own parent option.

        Returns:
            List of ``(NavNode, indented_label)`` pairs in DFS pre-order.
        """
        lang = language or settings.LANGUAGE_CODE
        nodes = cls._load_nodes(nav_type, lang)

        return NavNode.flatten_with_indent(
            nodes,
            label_func=lambda n: n.name,
            exclude_id=exclude_id,
            sort_key="sort_order",
        )

    @classmethod
    def invalidate_cache(cls, nav_type: str) -> None:
        """
        Invalidate all cached trees for the given nav_type across all languages.
        Called from ModelAdmin on save/delete.
        """
        keys = [_cache_key(nav_type, lang) for lang, _ in settings.LANGUAGES]
        cache.delete_many(keys)

    @classmethod
    def build_tree(cls, nav_type: str, language: str | None = None) -> list[NavNode]:
        """
        Build the tree structure for the specified nav_type.

        Args:
            nav_type: NavType value string (e.g. 'main', 'footer').
            language: Language code; falls back to default if not provided.

        Returns:
            Root nodes of the constructed tree.
        """
        lang = language or settings.LANGUAGE_CODE
        key = _cache_key(nav_type, lang)
        tree = cache.get(key)

        if tree is None:
            tree = NavNode.build_tree(cls._load_nodes(nav_type, lang), sort_key="sort_order")
            cache.set(key, tree, CACHE_TIMEOUT)

        return tree
