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
from django.utils.translation import get_language

from pinmok.core.constants import DEFAULT_SORT_ORDER
from pinmok.core.libs.tree import TreeNode
from pinmok.padmin.enums import TargetChoices
from pinmok.padmin.models import Nav

CACHE_TIMEOUT = 86400  # 24 hours
CACHE_KEY_PREFIX = "nav_"


def _cache_key(group: str, language: str) -> str:
    return f'{CACHE_KEY_PREFIX}_{group}_{language}'


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
    def _load_nodes(cls, group: str, lang: str) -> list[NavNode]:
        """Fetch nav items from database and convert to NavNode instances."""
        items = Nav.with_translations(
            Nav.objects.filter(group=group, is_visible=True)
        )
        return [
            NavNode(
                id=item.id,
                parent_id=item.parent_id,
                url=item.url,
                icon=item.icon,
                target=TargetChoices(item.target) if item.target in TargetChoices.values else TargetChoices.SELF,
                sort_order=item.sort_order,
                is_visible=item.is_visible,
                name=(t.name if (t := item.get_translation(lang)) else ''),
            )
            for item in items
        ]

    @classmethod
    def get_items(cls, group: str, language: str | None = None, exclude_id: int | None = None) -> list[tuple[NavNode, str]]:
        """
        Retrieve nav items and flatten in DFS pre-order with indented labels.

        Args:
            group: NavType value string (e.g. 'main', 'footer').
            language: Language code; falls back to default if not provided.
            exclude_id: If provided, exclude the node with this id from the result.
                    Used to prevent a node from appearing as its own parent option.

        Returns:
            List of ``(NavNode, indented_label)`` pairs in DFS pre-order.
        """
        lang = language or get_language() or settings.LANGUAGE_CODE
        nodes = cls._load_nodes(group, lang)

        return NavNode.flatten_with_indent(
            nodes,
            label_func=lambda n: n.name,
            exclude_id=exclude_id,
            sort_key="sort_order",
        )

    @classmethod
    def invalidate_cache(cls, group: str) -> None:
        """
        Invalidate all cached trees for the given group across all languages.
        Called from ModelAdmin on save/delete.
        """
        keys = [_cache_key(group, lang) for lang, _ in settings.LANGUAGES]
        cache.delete_many(keys)

    @classmethod
    def build_tree(cls, group: str, language: str | None = None) -> list[NavNode]:
        """
        Build the tree structure for the specified group.

        Args:
            group: NavType value string (e.g. 'main', 'footer').
            language: Language code; falls back to default if not provided.

        Returns:
            Root nodes of the constructed tree.
        """
        lang = language or get_language() or settings.LANGUAGE_CODE
        key = _cache_key(group, lang)
        tree = cache.get(key)

        if tree is None:
            tree = NavNode.build_tree(cls._load_nodes(group, lang), sort_key="sort_order")
            cache.set(key, tree, CACHE_TIMEOUT)

        return tree
