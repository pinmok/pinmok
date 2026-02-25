#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Menu service

Description:
  Menu registration and management system for the cmfadmin module.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-09
"""
import hashlib
import importlib
from uuid import uuid4

from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.db import transaction

from djangocmf.cmfadmin import constants
from djangocmf.cmfadmin.enums import MenuSource, MenuSyncMode
from djangocmf.cmfadmin.models import Menu, MenuPermission
from djangocmf.cmfadmin.service.authorization import PermissionService
from djangocmf.cmfadmin.utils.helper import get_valid_app_labels
from djangocmf.core.menu import MenuNode
from djangocmf.core.utils.tools import to_compact_case, to_snake_case


class AdminMenuImportError(Exception):
    """Raised when admin menu import fails."""
    pass


class MenuSynchronizer:
    """
    Menu synchronization service.

    Responsibilities:
    1. Fetch menu definitions from a single standard source.
    2. Normalize MenuNode instances (app_label, id, parent_id, validity).
    3. Persist menus into the database.
    4. Generate permissions exactly as in legacy implementation.
    """

    @classmethod
    def synchronize_menu(cls, app_label: str) -> dict:
        """
        Entry point for menu synchronization.
        """

        # Determine target apps
        valid_apps = get_valid_app_labels()
        if app_label == MenuSyncMode.SYNC_ALL:
            target_apps = valid_apps
        elif app_label in valid_apps:
            target_apps = {app_label}
        else:
            raise AdminMenuImportError(
                f"Invalid app_label '{app_label}', must be one of installed apps."
            )

        total_created = 0
        inserted_menus: list[MenuNode] = []

        with transaction.atomic():
            for app in target_apps:
                # 1. Fetch menu definitions
                nodes = cls._get_declarations(app)
                if not nodes:
                    continue

                # 2. Clear old menus and permissions
                cls._clear_app_menus(app)

                # 3. Normalize nodes: assign UUIDs, remap parent_id, validate
                normalized_nodes = cls._normalize_menu_nodes(nodes)

                # 4. Persist menus and permissions
                total_created += cls._insert_items(normalized_nodes, parent_db_id=None)

                inserted_menus.extend(normalized_nodes)

        return {
            "total_created": total_created,
            "menus": [
                {"app_label": m.app_label, "title": m.title, "url": m.url}
                for m in inserted_menus
            ],
        }

    # ---------- helpers ----------

    @staticmethod
    def _get_declarations(app_label: str) -> list[MenuNode]:
        """
        Adapter method to fetch menu definitions.

        Returns a list of MenuNode instances with minimal normalization:
        - app_label added
        """
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            return []

        try:
            module = importlib.import_module(f"{app_config.name}.menus")
        except ModuleNotFoundError:
            return []

        raw_nodes = getattr(module, "admin_menu", [])
        nodes: list[MenuNode] = []
        for node in raw_nodes:
            if isinstance(node, MenuNode):
                node.app_label = app_label  # fill in app_label
                nodes.append(node)
        return nodes

    @classmethod
    def _normalize_menu_nodes(cls, nodes: list[MenuNode]) -> list[MenuNode]:
        """
        Normalize a list of MenuNode instances for database insertion.

        This method performs the following operations:

        1. Assign a new unique UUID to each node's `id`.
           - Old IDs are mapped to new UUIDs using a local `id_map`.
           - Each app should call this independently to avoid ID conflicts.

        2. Remap `parent_id` of each node to the new UUIDs.
           - If a node's `parent_id` is missing or invalid, it is set to None (root level).
           - This ensures the parent-child relationship remains consistent.

        3. Return the updated list of nodes with normalized `id` and `parent_id`.

        Args:
            nodes (list[MenuNode]): Flat list of MenuNode instances to normalize.

        Returns:
            list[MenuNode]: The same list, with updated IDs and parent IDs.
        """
        if not nodes:
            return []

        # Local mapping of original ID -> new UUID
        id_map: dict[str, str] = {}

        # Step 1: remap node IDs
        for node in nodes:
            if node.id:
                original_id = node.id
                # Generate a new UUID for this node
                new_id = str(uuid4().hex)
                node.id = new_id
                id_map[original_id] = new_id

        # Step 2: remap parent_ids using the local id_map
        for node in nodes:
            if node.parent_id not in id_map:
                # If parent_id is invalid or missing, reset to None (top-level)
                node.parent_id = None
            else:
                # Map parent_id to new UUID
                node.parent_id = id_map[node.parent_id]

        return nodes

    _MENU_ASSIGNABLE_FIELDS: frozenset[str] = frozenset(
        f.name
        for f in Menu._meta.get_fields()
        if f.concrete
        and not f.auto_created
        and not f.primary_key
        and not f.is_relation
        and not getattr(f, 'auto_now', False)
        and not getattr(f, 'auto_now_add', False)
    )

    @classmethod
    def _prepare_menu_obj(cls, item: MenuNode, parent_db_id: int | None) -> Menu:
        """Prepare Menu instance from MenuNode"""
        data = {
            field: value
            for field in cls._MENU_ASSIGNABLE_FIELDS
            if hasattr(item, field) and (value := getattr(item, field)) is not None
        }
        data["parent_id"] = parent_db_id

        # build menu_key from app_label + normalized title [+ parent]
        app = getattr(item, "app_label", "").strip()
        safe_title = to_compact_case(getattr(item, "title", ""))
        # include parent_db_id only if same-title-under-different-parent to differ
        base_str = f"{app}:{safe_title}_{parent_db_id or 'root'}"
        data["menu_key"] = hashlib.md5(base_str.encode("utf-8")).hexdigest()
        return Menu(**data)

    @classmethod
    def _insert_items(cls, menu_nodes: list[MenuNode], parent_db_id: int | None) -> int:
        """
        Insert menu items into the database and generate corresponding permissions recursively.
        """
        created_count = 0
        current_level = [item for item in menu_nodes if item.parent_id == parent_db_id]
        if not current_level:
            return 0

        # Step 1: Prepare Menu objects to bulk_create
        to_create = [cls._prepare_menu_obj(item, parent_db_id) for item in current_level]

        # Step 2: Insert Menu objects
        Menu.objects.bulk_create(to_create, batch_size=100)
        created_items = list(Menu.objects.filter(menu_key__in=[m.menu_key for m in to_create]))
        created_count += len(created_items)

        # Step 3: Build mapping from temporary ID to DB ID
        created_map = {m.menu_key: m for m in created_items}
        for src in current_level:
            db = created_map[src.menu_key]
            src.db_id = db.id
            src.menu_key = db.menu_key
            for child in menu_nodes:
                if child.parent_id == src.id:
                    child.parent_id = db.id

        # Step 4: insert permissions
        parent_code_map: dict[int, str] = {}
        cls._generate_permissions(current_level, parent_code_map)

        # Step 5: Recursively insert child nodes
        for item in current_level:
            created_count += cls._insert_items(menu_nodes=menu_nodes, parent_db_id=item.db_id)

        return created_count

    @classmethod
    def _generate_permissions(cls, menu_nodes: list[MenuNode], parent_code_map: dict[int, str]):
        """
        Generate permissions for a list of menu nodes.
        Mixed scheme: default 'view' permission + custom permissions.
        Updates parent_code_map in-place for recursion.
        """
        for src in menu_nodes:
            # Skip root nodes
            if src.parent_id is None:
                continue

            # Record safe id for children
            parent_code_map[src.db_id] = to_snake_case(src.title)

            # Generate default view permission
            # build codename using app_label + compact title
            app = getattr(src, "app_label", "")
            safe_title = to_compact_case(src.title)
            codename = f"view_{app}:{safe_title}" if app else f"view_{safe_title}"

            # ensure uniqueness if collision still possible (rare)
            parent_id = src.parent_id
            while MenuPermission.objects.filter(codename=codename).exists() and parent_id:
                parent_safe = to_compact_case(parent_code_map.get(parent_id, ""))
                if parent_safe:  # only prepend if parent_safe is not empty
                    codename = f"view_{app}_{parent_safe}_{safe_title}" if app else f"view_{parent_safe}_{safe_title}"
                # Move up the tree
                parent_node = next((p for p in menu_nodes if p.db_id == parent_id), None)
                parent_id = getattr(parent_node, "parent_id", None) if parent_node else None

            MenuPermission.objects.update_or_create(
                codename=codename,  # use codename as lookup key
                defaults={
                    "menu_key": src.menu_key,  # update/overwrite menu_key as auxiliary info
                    "name": f"Can view {src.title}"
                }
            )

            # Generate custom permissions if defined
            if getattr(src, "permissions", None):
                for perm in src.permissions:
                    perm_code = perm.get("codename")
                    if not perm_code:
                        continue
                    perm_name = perm.get("name", f"Can {perm_code} {src.title}")
                    MenuPermission.objects.update_or_create(
                        codename=perm_code,  # perm_code is already the business codename
                        defaults={
                            "menu_key": src.menu_key,
                            "name": perm_name
                        }
                    )

    @staticmethod
    def _clear_app_menus(app_label: str):
        """
        Clear menus and permissions for a single app.
        NOTE:
        MenuPermission is linked to Menu by `menu_key`, NOT by ForeignKey.
        """
        menu_keys = Menu.objects.filter(app_label=app_label).values_list("menu_key", flat=True)
        MenuPermission.objects.filter(menu_key__in=menu_keys).delete()
        Menu.objects.filter(app_label=app_label).delete()


class AdminMenu:
    """
    AdminMenu assembles MenuItems from multiple sources,
    merges them, builds hierarchical tree and returns final menu structure.
    """

    @staticmethod
    def _load_from_database() -> list[MenuNode]:
        """
        Fetch active menu items from database and convert to MenuItem.
        """
        menu_data = Menu.objects.filter(is_active=True)
        menu_nodes: list[MenuNode] = []

        all_perms = MenuPermission.objects.all()
        perms_by_menu = {}

        for perm in all_perms:
            perms_by_menu.setdefault(perm.menu_key, []).append(perm.codename)

        for menu in menu_data:
            node = MenuNode.build_node(menu)
            node.source = MenuSource.DATABASE
            # Attach permission codes
            node.extra['perms'] = perms_by_menu.get(menu.menu_key, [])
            menu_nodes.append(node)
        return menu_nodes

    @staticmethod
    def _load_from_app_list(app_list: list[dict]) -> list[MenuNode]:
        """
        Convert Django admin app_list data to a flat list of MenuItem objects.
        Since the 'auth' module requires customized display titles, they are hardcoded here.
        """

        menu_nodes: list[MenuNode] = []

        for app in app_list:
            # Top-level menu (application)
            app_label = app.get('app_label')
            app_config = apps.get_app_config(app_label)
            app_item = MenuNode(
                id=app.get('app_label'),
                title=app_config.verbose_name,
                url=app.get('app_url'),
                icon=constants.AUTH_ICON,
                app_label=app_label,
                source=MenuSource.APP_LIST,
            )

            # Ensure admin menu order:
            # 1. Sites menu is manually registered with sort_order = 0
            # 2. Auth menu must always appear right after Sites
            # 3. Other apps keep default sort_order (10000) and follow registration order
            if app_label == 'auth':
                app_item.sort_order = 1

            menu_nodes.append(app_item)

            # Process models under the application
            for model in app.get('models', []):
                object_name = model.get('object_name')
                model_item = MenuNode(
                    id=object_name,
                    parent_id=app_item.id,
                    title=model.get('name') or object_name,
                    url=model.get('admin_url'),
                    app_label=app_label,
                    source=MenuSource.APP_LIST,
                )
                menu_nodes.append(model_item)

        return menu_nodes

    @classmethod
    def get_merged_nodes(cls, menu_nodes: list[MenuNode], app_list_menu_nodes: list[MenuNode]) -> list[MenuNode]:
        """
        Merge two lists of MenuItem objects with database items taking priority.

        Rules:
            - If a top-level app_list menu has the same app_label as a database menu, discard it.
            - If a child menu from app_list belongs to a known app_label in the database menus,
              update its parent_id to the corresponding database menu's id.
            - Append all valid items into the merged result.

        Returns:
            list[MenuNode]: Combined menu list for display, with conflicts resolved.
        """
        merged_nodes: list[MenuNode] = list(menu_nodes)

        # Build a mapping {app_label: first_root_id} for all database top-level menus
        app_label_to_db_id = {}
        for item in menu_nodes:
            if item.parent_id is None and item.app_label not in app_label_to_db_id:
                app_label_to_db_id[item.app_label] = item.id

        for app_menu_item in app_list_menu_nodes:
            if app_menu_item.parent_id is None:
                # Skip top-level app_list menus if a database menu with the same app_label exists
                if app_menu_item.app_label in app_label_to_db_id:
                    # Attach to the first root
                    app_menu_item.parent_id = app_label_to_db_id[app_menu_item.app_label]
                else:
                    merged_nodes.append(app_menu_item)
            else:
                # For child menus, if their parent exists in database, remap parent_id to database id
                if app_menu_item.parent_id in app_label_to_db_id:
                    app_menu_item.parent_id = app_label_to_db_id[app_menu_item.parent_id]
                merged_nodes.append(app_menu_item)

        return merged_nodes

    @staticmethod
    def _filter_by_permissions(menu_nodes: list[MenuNode], user: AbstractUser) -> list[MenuNode]:
        """
        Filter menu nodes according to user's permissions.
        """
        if not user.is_authenticated or not user.is_active:
            return []

        # Get all permissions of current user
        user_permissions = PermissionService.get_user_permissions(user)

        # If is superuser, skip filtering
        if user.is_superuser:
            return menu_nodes

        # Result list
        filtered_nodes: list[MenuNode] = []

        for node in menu_nodes:
            node_perms = node.extra.get("perms", [])
            # If no permissions defined, keep node
            if not node_perms:
                filtered_nodes.append(node)
                continue
            # Keep node if user has at least one permission
            if any(perm in user_permissions for perm in node_perms):
                filtered_nodes.append(node)

        return filtered_nodes

    @classmethod
    def get_menu(cls, app_list: list[dict], user: AbstractUser | None = None) -> list[MenuNode]:
        """
        Get final admin menu.
        """
        #  Load menu from database
        db_menus = cls._load_from_database()

        # Filter menu by permissions
        menu_nodes = cls._filter_by_permissions(db_menus, user)

        # Load menu from app_list
        app_list_menus_nodes = cls._load_from_app_list(app_list=app_list)

        # Merge two sources (db priority)
        merged_nodes = cls.get_merged_nodes(menu_nodes, app_list_menus_nodes)

        # Build hierarchical tree
        return MenuNode.build_tree(merged_nodes, sort_key='sort_order')
