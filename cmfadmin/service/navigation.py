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

from cmfadmin.constants import DEFAULT_SORT_ORDER
from cmfadmin.enums import TargetChoices
from cmfadmin.libs import TreeNode
from cmfadmin.models import Nav, NavItem as NavItemModel


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
    def _flatten_with_level(cls, nav_items: list[NavNode]) -> list[NavNode]:
        """
        Flatten the tree structure of `nav_items` and assign a `level` to each node.

        This method recursively traverses the tree, assigning a `level` value starting
        from 0 for the root nodes and incrementing by 1 for each subsequent level.

        Args:
            nav_items (list[NavNode]): A list of `NavItem` instances to be flattened.

        Returns:
            list[NavNode]: A flat list of `NavItem` instances with assigned `level` values.
        """

        roots = NavNode.build_tree(nav_items)
        result: list[NavNode] = []

        def _assign_level(node: NavNode, level: int) -> None:
            """
            Recursively assigns a `level` to a node and its children, and adds them to the result.

            Args:
                node (NavNode): The current `NavItem` node being processed.
                level (int): The current level to assign to the node.
            """

            # Assign level and add to result
            node.level = level
            node.title = "&emsp;" * level + node.name
            result.append(node)

            # Recursively assign level to child nodes
            for child in sorted(node.children, key=lambda x: x.sort_order):
                _assign_level(child, level + 1)

        # Start assigning levels from the root nodes
        for root in sorted(roots, key=lambda x: x.sort_order):
            _assign_level(root, 0)

        return result

    @classmethod
    def get_items(cls, nav: int | Nav) -> list[NavNode]:
        """
        Retrieve and flatten the nav items for the specified `nav` or `nav_id`.

        Args:
            nav (int | Nav): Either a `Nav` instance or a `nav_id` (integer or string).

        Returns:
            list[NavNode]: A flattened list of `NavItem` instances with assigned levels.
        """
        nav_items = NavItemModel.objects.filter(nav_id=nav.id if isinstance(nav, Nav) else nav).values(
            "id", "parent_id", "name", "url", "icon", "target", "sort_order", "is_visible"
        )
        return cls._flatten_with_level([NavNode(**item) for item in nav_items])

    @classmethod
    def build_tree(cls, nav: int | Nav) -> list[NavNode]:
        """
        Build the tree structure from the nav items for the specified `nav` or `nav_id`.

        Args:
            nav (int | Nav): Either a `Nav` instance or a `nav_id` (integer or string).

        Returns:
            list[NavNode]: A tree structure of `NavItem` instances.
        """
        return NavNode.build_tree(cls.get_items(nav))
