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
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.templatetags.static import static

from djangocmf.cmfadmin import constants
from djangocmf.cmfadmin.enums import MenuSyncMode, MenuSource, MenuPermissions
from djangocmf.cmfadmin.models import Menu, MenuPermission
from djangocmf.cmfadmin.service.authorization import PermissionService
from djangocmf.cmfadmin.utils.helper import get_model_fields, get_valid_app_labels
from djangocmf.core.libs.tree import TreeNode
from djangocmf.core.utils.tools import to_snake_case, to_compact_case

User = get_user_model()


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
    sort_order: int = 10000
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


class AdminMenuImportError(Exception):
    """Raised when admin menu import fails."""
    pass


class MenuSynchronizer:
    """
    Synchronize backend admin menus defined in app-level menus.py files.

    This class performs:
        1. Scan all installed apps for menus.py files.
        2. Parse menu definitions into a flat list of MenuItem instances.
        3. Detect duplicates, conflicts or invalid structures.
        4. Synchronize data into the database.

    Currently, it uses global class-level attributes and is intended
    for single-site projects. Future multi-site support may require redesign.
    """

    # Global temporary structures for one-time synchronization
    id_map: dict = {}
    items: list = []

    valid_app_labels: set[str] = get_valid_app_labels()

    @classmethod
    def _generate_id(cls, original_id: int | str | None = None) -> str:
        """
        Generate a unique UUID-based ID.
      N.,  If an original ID exists and has been generated before, reuse it.

        Args:
            original_id (str | None): Existing ID from input data.

        Returns:
            str: Generated or mapped unique ID.
        """
        if original_id and original_id in cls.id_map:
            return cls.id_map[original_id]
        new_id = str(uuid4().hex)
        if original_id:
            cls.id_map[original_id] = new_id
        return new_id

    @classmethod
    def _parse_node(cls, menu_node: dict, app_label: str, p_id: str | None = None):
        """
        Recursively parse a menu node, converting IDs and preserving hierarchy.

        Args:
            menu_node (dict): The menu node to parse.
            app_label (str): App label this menu belongs to.
            p_id (str | None): Parent ID from recursion context.

        Side Effects:
            Appends MenuItem instances to the class-level 'items' list.
        """
        original_id = menu_node.get("id")
        new_id = cls._generate_id(original_id=original_id)
        menu_node["id"] = new_id

        # Determine parent ID: prefer 'parent_id' field if exists, else use recursion context
        parent_id = menu_node.get("parent_id")
        new_parent_id = cls._generate_id(original_id=parent_id) if parent_id else p_id
        menu_node["parent_id"] = new_parent_id

        # Add additional tracking information
        menu_node["app_label"] = app_label

        # Build MenuItem node
        item = MenuNode.build_node(data=menu_node)
        cls.items.append(item)

        for child in menu_node.get("children", []):
            cls._parse_node(menu_node=child, app_label=app_label, p_id=new_id)

    @classmethod
    def _parse_custom_menu(cls, menu_data: list[dict], app_label: str = None) -> list[MenuNode]:
        """
        Parse menu data (tree or flat) into a flat list of MenuItem instances.
        Supports mixed cases with or without 'parent_id' fields.

        Args:
            menu_data (list[dict]): Raw menu data in tree or flat format.
            app_label (str): App label this menu belongs to.

        Returns:
            list[MenuNode]: Normalized flat list of MenuItem instances.
        """
        cls.id_map.clear()
        cls.items.clear()

        for node in menu_data:
            cls._parse_node(menu_node=node, app_label=app_label)

        return cls.items

    @classmethod
    def _get_sync_menus(cls, app_label: str) -> list[MenuNode]:
        """
        Scan installed apps and settings for admin menus of the specified app_label only.

        Args:
            app_label (str): The app label to scan for menus. This parameter is required
                             to avoid accidental full synchronization.

        Returns:
            list[MenuNode]: A flat list of all MenuItem instances parsed for the app.
        """
        custom_menus: list[MenuNode] = []

        # Scan the specified app's menus.py if exists
        for app_config in apps.get_app_configs():
            if app_config.label != app_label:
                continue

            try:
                module = importlib.import_module(f"{app_config.name}.menus")
            except ModuleNotFoundError:
                # If no menus.py, just skip silently
                continue

            admin_menu = getattr(module, constants.ADMIN_MENU_VAR_NAME, None)
            if not isinstance(admin_menu, list) or len(admin_menu) == 0:
                continue

            parsed_menu = cls._parse_custom_menu(menu_data=admin_menu, app_label=app_label)
            custom_menus.extend(parsed_menu)

        # Scan menus from settings.CMF_ADMIN_MENU['MENU_IMPORT_PATHS'] for this app_label only
        config = getattr(settings, constants.ADMIN_MENU_SETTING_KEY, {})
        menu_paths = config.get(constants.MENU_SETTINGS_KEY, [])

        for item in menu_paths:
            if not isinstance(item, dict):
                raise AdminMenuImportError(f"Each menu config item must be a dict: {item}")

            path = item.get(constants.PATH_KEY, '')
            item_app_label = item.get(constants.APP_LABEL_KEY, '')

            if not path or not item_app_label:
                raise AdminMenuImportError(f"Menu config item must have 'path' and 'app_label': {item}")
            elif item_app_label not in cls.valid_app_labels:
                raise AdminMenuImportError(f"App label '{item_app_label}' is not a valid installed application name.")

            if item_app_label != app_label:
                # Skip entries not matching requested app_label
                continue

            try:
                module_path, var_or_func = path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                value = getattr(module, var_or_func)
            except (ImportError, AttributeError) as e:
                raise AdminMenuImportError(f"Cannot import menu from path '{path}': {e}")

            if callable(value):
                value = value()

            if not isinstance(value, list):
                raise AdminMenuImportError(f"Menu from '{path}' must be a list, got {type(value)}")

            parsed_menu = cls._parse_custom_menu(menu_data=value, app_label=app_label)
            custom_menus.extend(parsed_menu)

        return custom_menus

    @classmethod
    def _get_sync_menus_all(cls) -> list[MenuNode]:
        """
        Scan all valid user apps and aggregate all menus into one list.
        """

        menus: list[MenuNode] = []

        for label in cls.valid_app_labels:
            try:
                menus.extend(cls._get_sync_menus(app_label=label))
            except AdminMenuImportError as e:
                print(f"Warning: failed to sync menus for {label}: {e}")

        return menus

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
    def _sanitize_menu(menu_nodes: list[MenuNode]) -> list[MenuNode]:
        """
        Sanitize and fix parent-child relationships in a flat list of MenuItem instances.

        This method ensures that each item's `parent_id` references a valid existing ID.
        If a `parent_id` does not match any existing item ID, it is reset to `None`,
        effectively promoting the item to a top-level menu.

        Args:
            menu_nodes (list[MenuNode]): Flat list of MenuItem instances to sanitize.

        Returns:
            list[MenuNode]: The same input list, modified in place for corrected parent_id references.
        """
        # Collect all valid ids from the current items
        valid_ids = {item.id for item in menu_nodes}

        for item in menu_nodes:
            if item.parent_id is not None and item.parent_id not in valid_ids:
                # If parent_id is invalid, reset it to None (top-level)
                item.parent_id = None

        return menu_nodes

    @staticmethod
    def _prepare_menu_obj(item, parent_db_id):
        """Prepare Menu instance from MenuNode"""
        model_fields = get_model_fields(Menu)
        data = {}
        for model_field in model_fields:
            if hasattr(item, model_field):
                value = getattr(item, model_field)
                if value is not None:
                    data[model_field] = value
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
        id_mapping = {src.id: db.id for src, db in zip(current_level, created_items)}
        for src, db in zip(current_level, created_items):
            src.db_id = db.id
            src.menu_key = db.menu_key
            for child in menu_nodes:
                if child.parent_id == src.id:
                    child.parent_id = id_mapping[src.id]

        # Step 4: insert permissions
        parent_code_map: dict[int, str] = {}
        cls._generate_permissions(current_level, parent_code_map)

        # Step 5: Recursively insert child nodes
        for item in current_level:
            created_count += cls._insert_items(menu_nodes=menu_nodes, parent_db_id=item.db_id)

        return created_count

    @classmethod
    def synchronize_menu(cls, app_label: str):
        """
        Synchronize and persist all custom admin menus defined in installed apps.
        This is atomic: deletion + insertion of menus and permissions are in one transaction.
        """
        if app_label != MenuSyncMode.SYNC_ALL and app_label not in cls.valid_app_labels:
            raise AdminMenuImportError(
                f"Invalid app_label '{app_label}', must be one of installed apps."
            )

        with transaction.atomic():  # Outer transaction ensures atomicity
            total_created = 0
            inserted_menus = []

            if app_label == MenuSyncMode.SYNC_ALL:
                all_menus = cls._get_sync_menus_all()
                # Clear all existing menu records and permissions
                Menu.objects.all().delete()

                for label in {m.app_label for m in all_menus}:
                    menus_for_label = [m for m in all_menus if m.app_label == label]
                    clear_menus = cls._sanitize_menu(menu_nodes=menus_for_label)
                    created = cls._insert_items(clear_menus, parent_db_id=None)
                    total_created += created
                    inserted_menus.extend([
                        {"app_label": label, "title": m.title, "url": m.url}
                        for m in clear_menus
                    ])
            else:
                sync_menus = cls._get_sync_menus(app_label=app_label)
                clear_menus = cls._sanitize_menu(menu_nodes=sync_menus)
                MenuPermission.objects.filter(menu__app_label=app_label).delete()
                Menu.objects.filter(app_label=app_label).delete()
                created = cls._insert_items(clear_menus, parent_db_id=None)
                total_created += created
                inserted_menus.extend([
                    {"app_label": app_label, "title": m.title, "url": m.url}
                    for m in clear_menus
                ])

            return {"total_created": total_created, "menus": inserted_menus}


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
                sort_order=1
            )
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
    def _filter_by_permissions(menu_nodes: list[MenuNode], user: User) -> list[MenuNode]:
        """
        Filter menu nodes according to user's permissions.
        """
        if user is None or not user.is_authenticated or not user.is_active:
            return []

        # Get all permissions of current user
        user_permissions = PermissionService.get_user_permissions(user)

        # If user has all permissions, skip filtering
        if MenuPermissions.ALL_PERMISSIONS in user_permissions:
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
    def get_menu(cls, app_list: list[dict], user: User | None = None) -> list[MenuNode]:
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
