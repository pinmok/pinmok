#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.menu

Description:
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/1/8
"""
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.templatetags.static import static

from djangocmf.core.constants import DEFAULT_SORT_ORDER
from djangocmf.core.libs.tree import TreeNode


@dataclass(kw_only=True)
class MenuNode(TreeNode["MenuNode"]):
    """
    Represents a single menu item within an admin menu group.

    Attributes:
        title (str): The display name of the menu item.
        url (str): The URL that the menu item points to.
        icon (str|None): Optional icon class for the menu item.
        sort_order (int): Sorting order within the group. Lower values appear first.
        is_active (bool): Whether the menu item is active.
        visible (bool): Whether the menu item is visible.
        remark (str | None): Optional remark or note for the menu item.
        source (str | None): Data source identifier for the menu item.
        app_label (str | None): App label this menu item belongs to.
        extra (dict): Extra custom attributes for the menu item.
    """
    title: str
    url: str | None = None
    icon: str | None = None
    sort_order: int = DEFAULT_SORT_ORDER
    is_active: bool = True
    visible: bool = True
    remark: str | None = None
    source: str | None = None
    app_label: str | None = None
    db_id: int | None = None  # The auto-incrementing ID in the database.
    menu_key: str | None = None
    permissions: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def __repr__(self):
        return f"<MenuItem id={self.id} name={self.title} source={self.source} app_label={self.app_label}>"

    def to_dict(
            self,
            include: list[str] | None = None,
            exclude: list[str] | None = None,
            depth: int | None = None
    ) -> dict[str, Any]:
        """
        Convert the menu item and its children to a dictionary.

        Args:
            include (list[str]|None): A list of attribute names to include.
            exclude (list[str]|None): A list of attribute names to exclude.
            depth (int|None): Maximum depth to recursively convert children.
        Returns:
            dict[str, Any]: A dictionary representation of the menu item.

        Raises:
            ValueError: If both `include` and `exclude` are provided.
        """
        data = super().to_dict(include=include, exclude=exclude, depth=depth)
        data['sprite_path'] = self.sprite_path
        return data

    @property
    def sprite_path(self) -> str:
        """
        Return the sprite file path for the current menu item's icon.

        Rules:
            - If the icon name starts with "tabler-", it uses the built-in system sprite.
            - Otherwise, it uses the user-defined custom sprite file.

        The custom sprite file path can be configured via the `CMF_CUSTOM_SPRITE`
        setting in Django settings. If not defined, it defaults to 'svg/custom_sprite.svg'.

        Returns:
            str: URL path to the corresponding sprite file.
        """
        if self.icon and self.icon.startswith("tabler-"):
            return static('admin/svg/sprite.svg')
        else:
            return static(getattr(settings, 'CMF_CUSTOM_SPRITE', 'svg/custom_sprite.svg'))


def menu(
        key,
        *,
        title,
        url: str | None = None,
        parent_key: str | None = None,
        sort_order: int = DEFAULT_SORT_ORDER,
        icon: str | None = None,
        remark: str | None = None,
        extra: dict[str, Any] | None = None,
) -> MenuNode:
    """
    Declare a raw admin menu item.

    This function MUST:
    - have no side effects
    - not resolve URLs
    - not touch permissions, DB, or settings
    - not depend on runtime context

    It only returns a MenuDeclaration object.
    """

    # ---- hard validation (fail fast) ----

    if not isinstance(key, str) or not key:
        raise ValueError("menu(): 'key' must be a non-empty string")

    if not isinstance(title, str) or not title:
        raise ValueError("menu(): 'title' must be a non-empty string")

    if parent_key is not None and not isinstance(parent_key, str):
        raise ValueError("menu(): 'parent_key' must be a string or None")

    if not isinstance(sort_order, int):
        raise ValueError("menu(): 'sort_order' must be an integer")

    if url is not None and not isinstance(url, str):
        raise ValueError("menu(): 'url' must be a string, or None")

    if extra is not None and not isinstance(extra, dict):
        raise ValueError("menu(): 'extra' must be a dict or None")

    # ---- normalize ----

    return MenuNode(
        id=key,
        title=title,
        url=url,
        parent_id=parent_key,
        sort_order=sort_order,
        icon=icon,
        remark=remark,
        extra=extra or {},
    )
