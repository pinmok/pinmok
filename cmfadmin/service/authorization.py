#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorization module

Description:
  Unified permission management for Django backend.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-09-09
"""
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core.exceptions import ValidationError
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from cmfadmin.enums import PermissionSource
from cmfadmin.libs import TreeNode
from cmfadmin.models import MenuPermission, Menu

User = get_user_model()


@dataclass(kw_only=True)
class PermissionNode(TreeNode["PermissionNode"]):
    """
    Tree node specialized for CustomPermission.
    Only contains fields relevant to permission management.
    """
    title: str
    source: PermissionSource
    code: str | None = None
    category: str | None = None
    checked: bool = False
    db_id: int | None = None
    sort_order: int = 10000
    extra: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f'<PermissionNode id={self.id!r} parent_id={self.parent_id!r} title={self.title!r} '
            f'category={self.category!r} code={self.code!r} source={self.source!r} checked={self.checked!r}>'
        )

    def to_dict(
            self,
            include: list[str] | None = None,
            exclude: list[str] | None = None,
            depth: int | None = None
    ) -> dict[str, Any]:
        """
        Convert node to dict, fully compatible with TreeNode signature.
        Frontend can dynamically add 'checked' or other UI fields if needed.
        """
        # Call parent to_dict to respect include/exclude/depth logic
        data = super().to_dict(include=include, exclude=exclude, depth=depth)

        # Pre-convert translations for JSON serialization
        for k, v in data.items():
            if isinstance(v, Promise):
                data[k] = str(v)
        return data


class PermissionRegistry:
    """
    Central registry for user-defined custom permissions.
    Can be used in AppConfig to register permissions during app initialization.
    """

    _registry: list[dict[str, Any]] = []

    @classmethod
    def register_permissions(cls, permissions: Iterable[dict[str, Any]]) -> None:
        """
        Register a batch of custom permissions.

        Args:
            permissions: iterable of dicts with keys:
                - code (str): unique identifier, e.g. "custom:reports:view"
                - title (str): human-readable name
                - parent_id (str|None): optional parent node id
                - category (str|None): optional grouping
                - description (str|None): optional description

        Raises:
            ValidationError: if required fields are missing or duplicate codes found
        """
        if not permissions:
            return

        codes = [p.get("code") for p in permissions]
        if not all(codes):
            raise ValidationError(_("Each permission must have a non-empty 'code'."))
        if len(set(codes)) != len(codes):
            raise ValidationError(_("Duplicate permission codes in input."))

        # Optional: check against already registered codes
        existing_codes = {p["code"] for p in cls._registry}
        duplicates = set(codes) & existing_codes
        if duplicates:
            raise ValidationError(_("Duplicate codes already registered: %(codes)s") % {"codes": ", ".join(duplicates)})

        # Add to registry
        cls._registry.extend(permissions)

    @classmethod
    def get_all(cls) -> list[dict[str, Any]]:
        """
        Return all registered custom permissions.
        """
        return cls._registry.copy()


class PermissionService:

    @staticmethod
    def _get_system_permissions() -> list[PermissionNode]:
        """
        Fetch all Django system permissions and convert them into PermissionNode list.
        Root nodes: one per app_label, parent_id=None
        Model nodes: one per model under its app root
        Leaf nodes: permissions under model node
        """
        exclude_pairs = {
            ("admin", "logentry"),
            ("auth", "permission"),
            ("contenttypes", "contenttype"),
            ("sessions", "session"),
            ("cmfadmin", "navitem"),
            ("cmfadmin", "config"),
            ("cmfadmin", "menu"),
            ("cmfadmin", "uploadfile"),
            ("cmfadmin", "custompermission"),
            ("cmfadmin", "menupermission"),
        }

        permissions = Permission.objects.select_related("content_type").all()
        nodes: list[PermissionNode] = []

        seen_apps: dict[str, PermissionNode] = {}
        seen_models: dict[tuple[str, str], PermissionNode] = {}

        for perm in permissions:
            app_label: str = perm.content_type.app_label
            model_name: str = str(perm.content_type.model)

            if (app_label, model_name) in exclude_pairs:
                continue

            # ensure app root node exists
            if app_label not in seen_apps:
                try:
                    app_config = apps.get_app_config(app_label)
                    app_verbose = app_config.verbose_name
                except LookupError:
                    app_verbose = app_label

                app_node = PermissionNode(
                    id=f"sys_app_{app_label}",
                    parent_id=None,
                    title=app_verbose,
                    source=PermissionSource.SYSTEM,
                    category=app_label,
                )
                nodes.append(app_node)
                seen_apps[app_label] = app_node

            # ensure model node exists
            model_key = (app_label, model_name)
            if model_key not in seen_models:
                model_class = perm.content_type.model_class()
                if model_class is not None:
                    model_verbose = model_class._meta.verbose_name_plural
                else:
                    model_verbose = model_name

                model_node = PermissionNode(
                    id=f"sys_model_{app_label}_{model_name}",
                    parent_id=f"sys_app_{app_label}",
                    title=model_verbose,
                    source=PermissionSource.SYSTEM,
                    category=app_label,
                    code=None,
                )
                nodes.append(model_node)
                seen_models[model_key] = model_node

            # create permission leaf node under model
            leaf_node = PermissionNode(
                id=f"sys_{perm.id}",
                parent_id=f"sys_model_{app_label}_{model_name}",
                title=_(perm.name),
                source=PermissionSource.SYSTEM,
                code=f"{app_label}.{perm.codename}",
                category=app_label,
                db_id=perm.id,
                extra={
                    "content_type_id": getattr(perm.content_type, "id", None),
                    "model": model_name,
                },
            )
            nodes.append(leaf_node)

        return nodes

    @staticmethod
    def _get_menu_permissions() -> list[PermissionNode]:
        """
        Fetch all menu permissions and convert them into PermissionNode objects.
        Each menu has one associated permission, and hierarchy follows the menu tree.
        """
        # Load all menus once and build mapping by menu_key
        menus = list(Menu.objects.all())
        menu_map = {m.menu_key: m for m in menus}

        nodes: list[PermissionNode] = []
        seen_menus: dict[str, PermissionNode] = {}

        permissions = MenuPermission.objects.all()
        for perm in permissions:
            menu = menu_map.get(perm.menu_key)
            if not menu:
                continue

            # create virtual menu node if not exists
            if menu.menu_key not in seen_menus:
                menu_node = PermissionNode(
                    id=f"menu_{menu.id}",
                    parent_id=f"menu_{menu.parent_id}" if menu.parent_id else None,
                    title=_(menu.title),
                    source=PermissionSource.MENU,
                    category=getattr(menu, "app_label", None),
                    db_id=menu.id,
                    sort_order=getattr(menu, "sort_order", 10000),
                )
                nodes.append(menu_node)
                seen_menus[menu.menu_key] = menu_node

            # attach permission node under menu node
            perm_node = PermissionNode(
                id=f"perm_{perm.id}",
                parent_id=f"menu_{menu.id}",
                title=_(perm.name),
                source=PermissionSource.MENU,
                code=perm.code,
                category=getattr(menu, 'app_label', None),
                db_id=perm.id,
                sort_order=getattr(menu, 'sort_order', 10000),
                extra={
                    "menu_key": perm.menu_key,
                    "menu_id": getattr(menu, "id", None),
                }
            )
            nodes.append(perm_node)

        return nodes

    @staticmethod
    def _get_custom_permissions() -> list[PermissionNode]:
        """
        Load user-registered custom permissions from PermissionRegistry
        and convert them into PermissionNode instances.
        """
        nodes: list[PermissionNode] = []
        for perm in PermissionRegistry.get_all():
            node = PermissionNode(
                id=f"custom_{perm['code']}",
                parent_id=perm.get("parent_id", None),
                title=perm.get("title", perm["code"]),
                source=PermissionSource.CUSTOM,
                code=perm["code"],
                category=perm.get("category"),
                db_id=perm.get("id", None),
                extra={"description": perm.get("description")}
            )
            nodes.append(node)
        return nodes

    @staticmethod
    def _get_instance_permissions(instance: User | Group) -> list[str]:
        # Only allow User or Group
        if isinstance(instance, (User, Group)):
            # Access the permission field defined in MenuPermission.PERMISSION_FIELD
            perm_qs = getattr(instance, MenuPermission.PERMISSION_RELATED_NAME).all()
            return list(perm_qs.values_list('code', flat=True))
        else:
            raise TypeError(_("instance must be a User or Group"))

    @classmethod
    def _get_merged_permissions(cls, instance: User | Group) -> list[PermissionNode]:
        """
        Merge menu, system, and custom permissions into a flat list.
        Mark nodes checked according to the user's assigned permissions.
        """
        menu_nodes = cls._get_menu_permissions()
        system_nodes = cls._get_system_permissions()
        custom_nodes = cls._get_custom_permissions()

        # Merge all permissions into a single flat list
        all_nodes: list[PermissionNode] = []
        all_nodes.extend(menu_nodes)
        all_nodes.extend(system_nodes)
        all_nodes.extend(custom_nodes)

        # Build menu root mapping (category/app_label -> menu root id)
        menu_root_map = {n.category: n.id for n in menu_nodes if n.parent_id is None and n.category}

        # Fetch codes assigned to this user
        user_codes = set(cls._get_instance_permissions(instance))

        # Adjust system parent_id and mark checked
        for node in all_nodes:
            if node.parent_id is None and node.source == PermissionSource.SYSTEM:
                if node.category in menu_root_map:
                    node.parent_id = menu_root_map[node.category]

            # Mark checked if user has permission
            node.checked = node.code in user_codes

        return all_nodes

    @classmethod
    def get_permission_tree_for_instance(cls, user_or_group: User | Group) -> list[PermissionNode]:
        all_nodes = cls._get_merged_permissions(user_or_group)
        return PermissionNode.build_tree(all_nodes)
