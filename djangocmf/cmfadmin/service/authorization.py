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
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Iterable

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin as DjangoPermissionMixin
from django.contrib.auth.models import Permission, Group
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpRequest
from django.utils.functional import Promise
from django.utils.translation import gettext as _

from djangocmf.cmfadmin.enums import PermissionSource
from djangocmf.cmfadmin.models import MenuPermission, Menu
from djangocmf.core.libs.tree import TreeNode

User = get_user_model()


@dataclass(kw_only=True)
class PermissionNode(TreeNode["PermissionNode"]):
    """
    Tree node specialized for CustomPermission.
    Only contains fields relevant to permission management.
    """
    title: str | Promise
    source: PermissionSource
    codename: str | None = None
    category: str | None = None
    checked: bool = False
    db_id: int | None = None
    sort_order: int = 10000
    extra: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f'<PermissionNode id={self.id!r} parent_id={self.parent_id!r} title={self.title!r} '
            f'category={self.category!r} codename={self.codename!r} source={self.source!r} checked={self.checked!r}>'
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
    _source_map: dict[type, str] = {}

    @classmethod
    def register_permissions(cls, permissions: Iterable[dict[str, Any]]) -> None:
        """
        Register a batch of custom permissions.
        """
        if not permissions:
            return

        codes = [p.get("codename") for p in permissions]
        if not all(codes):
            raise ValidationError("Each permission must have a non-empty 'codename'.")
        if len(set(codes)) != len(codes):
            raise ValidationError("Duplicate permission codes in input.")

        # Optional: check against already registered codes
        existing_codes = {p["codename"] for p in cls._registry}
        duplicates = set(codes) & existing_codes
        if duplicates:
            raise ValidationError(f"Duplicate codes already registered: {', '.join(duplicates)}")

        # Add to registry
        cls._registry.extend(permissions)

    @classmethod
    def get_all(cls) -> list[dict[str, Any]]:
        """
        Return all registered custom permissions.
        """
        return cls._registry.copy()

    @classmethod
    def register_source(cls, model_class: type, attr_name: str) -> None:
        """
        Register a source attribute or method for custom permissions of a given model class.

        Args:
            model_class: the class (e.g. User or Group)
            attr_name: attribute or method name that returns the custom permission queryset
        """
        if not model_class or not attr_name:
            raise ValidationError("Both model_class and attr_name are required.")
        cls._source_map[model_class] = attr_name

    @classmethod
    def get_source(cls, model_class: type) -> str | None:
        """
        Retrieve the registered custom permission source name for the given model class.
        """
        return cls._source_map.get(model_class)


class PermissionService:
    CACHE_KEY_PREFIX = "admin:user_perms_"
    CACHE_TIMEOUT = timedelta(days=1).total_seconds()

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
                    codename=None,
                )
                nodes.append(model_node)
                seen_models[model_key] = model_node

            # create permission leaf node under model
            leaf_node = PermissionNode(
                id=f"sys_{perm.id}",
                parent_id=f"sys_model_{app_label}_{model_name}",
                title=_(perm.name),
                source=PermissionSource.SYSTEM,
                codename=f"{app_label}.{perm.codename}",
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
        for menu in menus:
            if menu.menu_key not in seen_menus:
                parent_id = f"menu_{menu.parent_id}" if menu.parent_id else None
                menu_node = PermissionNode(
                    id=f"menu_{menu.id}",
                    parent_id=parent_id,
                    title=_(menu.title),
                    source=PermissionSource.MENU,
                    category=getattr(menu, "app_label", None),
                    db_id=menu.id,
                    sort_order=getattr(menu, 'sort_order', 10000),
                )
                nodes.append(menu_node)
                seen_menus[menu.menu_key] = menu_node

        permissions = MenuPermission.objects.all()
        for perm in permissions:
            menu = menu_map.get(perm.menu_key)
            if not menu:
                continue
            perm_node = PermissionNode(
                id=f"perm_{perm.id}",
                parent_id=f"menu_{menu.id}",
                title=_(perm.name),
                source=PermissionSource.MENU,
                codename=perm.codename,
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
                id=f"custom_{perm['codename']}",
                parent_id=perm.get("parent_id", None),
                title=perm.get("title", perm["codename"]),
                source=PermissionSource.CUSTOM,
                codename=perm["codename"],
                category=perm.get("category"),
                db_id=perm.get("id", None),
                extra={"description": perm.get("description")}
            )
            nodes.append(node)
        return nodes

    @staticmethod
    def _get_instance_permissions(instance: User | Group) -> set[str]:
        """
        Collect permission identifiers from three sources:
          - system permissions (Django auth): "app_label.codename"
          - menu permissions (MenuPermission.codename) via MenuPermission.PERMISSION_RELATED_NAME
          - custom permissions (if instance has a 'custom_permissions' related manager, use its 'codename' field)

        Returns a de-duplicated list of strings.
        """

        # system permissions
        if isinstance(instance, User):
            sys_qs = instance.user_permissions.select_related("content_type").all()
        elif isinstance(instance, Group):
            sys_qs = instance.permissions.select_related("content_type").all()
        else:
            return set()

        codes: set[str] = set()

        # system permissions
        for app_label, codename in sys_qs.values_list("content_type__app_label", "codename"):
            if app_label and codename:
                codes.add(f"{app_label}.{codename}")

        # menu permissions
        menu_related = getattr(MenuPermission, "PERMISSION_RELATED_NAME", None)
        if menu_related and hasattr(instance, menu_related):
            menu_qs = getattr(instance, menu_related).all()
            codes.update(filter(None, menu_qs.values_list("codename", flat=True)))

        # custom permissions (resolved via PermissionRegistry)
        related_attr = PermissionRegistry.get_source(type(instance))
        if related_attr:
            target = getattr(instance, related_attr, None)
            if target is not None:
                if callable(target):
                    result = target()
                    if hasattr(result, "values_list"):
                        codes.update(filter(None, result.values_list("codename", flat=True)))
                elif hasattr(target, "all"):
                    codes.update(filter(None, target.all().values_list("codename", flat=True)))

        # remove duplicates
        return codes

    @classmethod
    def _get_merged_permissions(cls, instance: User | Group) -> list[PermissionNode]:
        """
        Merge menu, system, and custom permissions into a flat list.
        Ensure tree completeness by preserving virtual menu roots (even if they have no real permission)
        and reparenting system-root children under corresponding menu roots when available.
        Mark nodes.checked according to instance's assigned permission codes.
        """
        # load source nodes
        menu_nodes = cls._get_menu_permissions()  # menu nodes include virtual menu nodes
        system_nodes = cls._get_system_permissions()
        custom_nodes = cls._get_custom_permissions()

        # flat combined list
        all_nodes: list[PermissionNode] = []
        all_nodes.extend(menu_nodes)
        all_nodes.extend(system_nodes)
        all_nodes.extend(custom_nodes)

        # build mapping: for menu roots (by category) -> root node id
        menu_root_map: dict[str, str] = {}
        for node in menu_nodes:
            # a menu root is a menu node with no parent_id and has a category (app_label)
            if node.parent_id is None and node.category:
                if node.category not in menu_root_map:
                    menu_root_map[node.category] = node.id

        # fetch permission codes assigned to the instance
        user_codes = cls._get_instance_permissions(instance)

        # list of nodes to remove from final result (e.g. system virtual roots reparented)
        to_delete: list[PermissionNode] = []

        # mark checked and reparent system-root children if corresponding menu root exists
        for node in all_nodes:
            # mark checked if node.codename in user's codes (codename may be None for virtual menu nodes)
            node.checked = bool(node.codename and node.codename in user_codes)

        # handle reparenting of system-root children to menu roots (and schedule system roots for removal)
        for node in list(all_nodes):  # iterate over a snapshot
            if node.parent_id is None and node.source == PermissionSource.SYSTEM:
                # if there is a menu root for this node's category, move its children under that menu root
                target_menu_root_id = menu_root_map.get(node.category)
                if target_menu_root_id:
                    for child in all_nodes:
                        if child.parent_id == node.id:
                            child.parent_id = target_menu_root_id
                    # mark the system root node for deletion (we don't want to render system-root duplicates)
                    to_delete.append(node)

        # return nodes excluding those scheduled for deletion
        result = [n for n in all_nodes if n not in to_delete]
        return result

    @classmethod
    def get_permission_tree_for_instance(cls, user_or_group: User | Group) -> list[PermissionNode]:
        all_nodes = cls._get_merged_permissions(user_or_group)
        return PermissionNode.build_tree(all_nodes)

    @classmethod
    def save_menu_permissions(cls, user_or_group: User | Group, menu_ids: list) -> None:
        """
        Save menu permissions for a user or group.
        Uses dynamic related name defined in MenuPermission.PERMISSION_RELATED_NAME.
        """

        # Clean invalid IDs
        ids = [int(mid) for mid in menu_ids if mid.isdigit()]

        # Get dynamic field name
        field_name = MenuPermission.PERMISSION_RELATED_NAME

        # Validate that the field exists
        if not hasattr(user_or_group, field_name):
            raise AttributeError(
                f"Model '{user_or_group.__class__.__name__}' must define a ManyToMany field '{field_name}'"
            )

        manager = getattr(user_or_group, field_name)

        # Clear all if no valid IDs
        if not ids:
            manager.clear()
            return

        # Set new relations
        manager.set(manager.model.objects.filter(id__in=ids))

    @classmethod
    def save_custom_permissions(cls, user_or_group: User | Group, custom_ids: list) -> None:
        """
        Save custom permissions for a User or Group.
        Field/method name is determined via PermissionRegistry.get_source().
        """
        if not custom_ids:
            # nothing to save
            source_attr = PermissionRegistry.get_source(type(user_or_group))
            if source_attr:
                getattr(user_or_group, source_attr).clear()
            return

        source_attr = PermissionRegistry.get_source(type(user_or_group))
        if not source_attr:
            raise AttributeError(
                f"Custom permission source for {user_or_group.__class__.__name__} is not registered in PermissionRegistry."
            )

        manager = getattr(user_or_group, source_attr)
        manager.set(manager.model.objects.filter(id__in=[int(cid) for cid in custom_ids if str(cid).isdigit()]))

    @classmethod
    def get_user_permissions(cls, user: User) -> set[str]:
        """
        Return all merged permissions for a user.
        Combines user-level and group-level permissions,
        supports custom/menu/system permission sources,
        and caches results for one day.
        """
        if not user or not user.is_active:
            return set()

        cache_key = f"{cls.CACHE_KEY_PREFIX}{user.pk}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Collect user-level permissions
        user_codes = cls._get_instance_permissions(user)

        # Collect group-level permissions
        group_codes: set[str] = set()
        for group in user.groups.all().only("id"):
            group_codes |= cls._get_instance_permissions(group)

        # Merge and cache
        all_codes = user_codes | group_codes
        cache.set(cache_key, all_codes, cls.CACHE_TIMEOUT)

        return all_codes

    @classmethod
    def clear_user_cache(cls, user_id: int | None = None) -> None:
        """
        Clear cached permissions for a specific user or all users.
        """
        if user_id:
            cache.delete(f"{cls.CACHE_KEY_PREFIX}{user_id}")

    @classmethod
    def has_permission(cls, user: User, perm_codes: str | Sequence[str]) -> bool:
        """
        Check whether the user has a given permission (system or custom/menu).

        Args:
            user: User instance
            perm_codes: Single codename or list of codes
        Returns:
            bool: True if user has permission, False otherwise
        """
        if not user or not user.is_active:
            return False

        # Superuser shortcut
        if user.is_superuser:
            return True

        # Fetch all permissions for user (system + menu + custom)
        user_perms = cls.get_user_permissions(user)

        # Normalize perm_codes to tuple
        if isinstance(perm_codes, str):
            perm_codes = (perm_codes,)
        else:
            perm_codes = tuple(perm_codes)

        return any(codename in user_perms for codename in perm_codes)


def permission_required(
        perms: str | Sequence[str] = None,
        login_url=None,
        raise_exception: bool = False,
        superuser_only: bool = False
):
    """
    Decorator for function-based views.
    - Accepts single or multiple permission codes.
    - Returns 403 if user lacks all required permissions.
    - If superuser_only=True, only superusers are allowed, others denied.
    """

    def decorator(view_func):
        def check_perms(user):
            if user.is_superuser:
                return True

            # Superuser-only mode: short-circuit everything else
            if superuser_only and not user.is_superuser:
                if raise_exception:
                    raise PermissionDenied
                return False

            # Normal permission check
            if not PermissionService.has_permission(user, perms):
                if raise_exception:
                    raise PermissionDenied
                return False

            # Allow by default if superuser or no perms specified
            return True

        return user_passes_test(check_perms, login_url=login_url)(view_func)

    return decorator


class PermissionRequiredMixin(DjangoPermissionMixin):
    """
    Mixin for class-based views.
    Usage:
        class MyView(PermissionRequiredMixin, TemplateView):
            permission_required = ["app_label.codename", "menu_code"]
    """
    request: HttpRequest  # type hint for IDE
    superuser_only: bool = False

    def has_permission(self) -> bool:
        """Core permission check logic."""
        if self.superuser_only:
            return self.request.user.is_superuser

        if not self.permission_required:
            return True  # Allow by default if not specified

        perms = self.get_permission_required()
        return PermissionService.has_permission(self.request.user, perms)
