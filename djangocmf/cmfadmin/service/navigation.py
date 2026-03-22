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

from djangocmf.cmfadmin.enums import TargetChoices
from djangocmf.cmfadmin.models import Nav, NavItem as NavItemModel
from djangocmf.core.constants import DEFAULT_SORT_ORDER
from djangocmf.core.libs.tree import TreeNode


@dataclass(kw_only=True)
class NavNode(TreeNode['NavNode']):
    name: str
    url: str = ''
    icon: str = ''
    target: TargetChoices = TargetChoices.SELF
    sort_order: int = DEFAULT_SORT_ORDER
    is_visible: bool = True
    level: int = 0
    title: str = ''

    def __repr__(self):
        return f"<NavItem id={self.id} name={self.name} level={self.level}>"


class NavService:

    @classmethod
    def _load_nodes(cls, nav: int | Nav) -> list[NavNode]:
        """Fetch nav items from database and convert to NavNode instances."""
        nav_items = NavItemModel.objects.filter(
            nav_id=nav.id if isinstance(nav, Nav) else nav
        ).values("id", "parent_id", "name", "url", "icon", "target", "sort_order", "is_visible")
        return [NavNode(**item) for item in nav_items]

    @classmethod
    def get_items(cls, nav: int | Nav) -> list[tuple[NavNode, str]]:
        """
        Retrieve nav items and flatten in DFS pre-order with indented labels.

        Args:
            nav: Either a ``Nav`` instance or a nav_id.

        Returns:
            List of ``(NavNode, indented_label)`` pairs in DFS pre-order.
        """
        return NavNode.flatten_with_indent(
            cls._load_nodes(nav),
            label_func=lambda n: n.name,
            sort_key="sort_order",
        )

    @classmethod
    def build_tree(cls, nav: int | Nav) -> list[NavNode]:
        """
        Build the tree structure from the nav items for the specified nav.

        Args:
            nav: Either a ``Nav`` instance or a nav_id.

        Returns:
            Root nodes of the constructed tree.
        """
        return NavNode.build_tree(cls._load_nodes(nav), sort_key="sort_order")
