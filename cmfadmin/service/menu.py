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
import importlib
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.db import transaction

from .. import constants
from ..enums import MenuSyncMode, MenuSource
from ..libs import TreeNode
from ..models import Menu
from ..utils.helper import get_model_fields, get_valid_app_labels


@dataclass(kw_only=True)
class MenuItem(TreeNode["MenuItem"]):
    """
    Represents a single menu item within an admin menu group.

    Attributes:
        title (str): The display name of the menu item.
        url (str): The URL that the menu item points to.
        icon (str|None): Optional icon class for the menu item.
        sort_order (int): Sorting order within the group. Lower values appear first.
        permission (list[str]): List of permission codes required to view this menu item.
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
    permission: list[str] = field(default_factory=list)
    is_active: bool = True
    visible: bool = True
    remark: str | None = None
    source: str | None = None
    app_label: str | None = None
    db_id: int | None = None  # The auto-incrementing ID in the database.
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
        return super().to_dict(include=include, exclude=exclude, depth=depth)


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
        If an original ID exists and has been generated before, reuse it.

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
        item = MenuItem.build_node(data=menu_node)
        cls.items.append(item)

        for child in menu_node.get("children", []):
            cls._parse_node(menu_node=child, app_label=app_label, p_id=new_id)

    @classmethod
    def _parse_custom_menu(cls, menu_data: list[dict], app_label: str = None) -> list[MenuItem]:
        """
        Parse menu data (tree or flat) into a flat list of MenuItem instances.
        Supports mixed cases with or without 'parent_id' fields.

        Args:
            menu_data (list[dict]): Raw menu data in tree or flat format.
            app_label (str): App label this menu belongs to.

        Returns:
            list[MenuItem]: Normalized flat list of MenuItem instances.
        """
        cls.id_map.clear()
        cls.items.clear()

        for node in menu_data:
            cls._parse_node(menu_node=node, app_label=app_label)

        return cls.items

    @classmethod
    def _get_sync_menus(cls, app_label: str) -> list[MenuItem]:
        """
        Scan installed apps and settings for admin menus of the specified app_label only.

        Args:
            app_label (str): The app label to scan for menus. This parameter is required
                             to avoid accidental full synchronization.

        Returns:
            list[MenuItem]: A flat list of all MenuItem instances parsed for the app.
        """
        custom_menus: list[MenuItem] = []

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
    def _get_sync_menus_all(cls) -> list[MenuItem]:
        """
        Scan all valid user apps and aggregate all menus into one list.
        """

        menus: list[MenuItem] = []

        for label in cls.valid_app_labels:
            try:
                menus.extend(cls._get_sync_menus(app_label=label))
            except AdminMenuImportError as e:
                print(f"Warning: failed to sync menus for {label}: {e}")

        return menus

    @staticmethod
    def _sanitize_menu(menu_items: list[MenuItem]) -> list[MenuItem]:
        """
        Sanitize and fix parent-child relationships in a flat list of MenuItem instances.

        This method ensures that each item's `parent_id` references a valid existing ID.
        If a `parent_id` does not match any existing item ID, it is reset to `None`,
        effectively promoting the item to a top-level menu.

        Args:
            menu_items (list[MenuItem]): Flat list of MenuItem instances to sanitize.

        Returns:
            list[MenuItem]: The same input list, modified in place for corrected parent_id references.
        """
        # Collect all valid ids from the current items
        valid_ids = {item.id for item in menu_items}

        for item in menu_items:
            if item.parent_id is not None and item.parent_id not in valid_ids:
                # If parent_id is invalid, reset it to None (top-level)
                item.parent_id = None

        return menu_items

    @classmethod
    def _insert_items(cls, menu_items: list[MenuItem], parent_db_id: int | None) -> None:
        """
        Batch insert menu items (optimized recursive version).

        Logic:
        1. Process nodes level by level.
        2. Maintain in-memory ID -> database ID mapping.
        3. Handle child levels recursively.

        Args:
            menu_items (list[MenuItem]): Flat list of all menu items to insert.
            parent_db_id (int | None): Database ID of parent node, None for root level.
        """
        current_level = [
            item for item in menu_items
            if item.parent_id == parent_db_id
        ]
        if not current_level:
            return

        model_fields = get_model_fields(Menu)
        to_create = []
        for item in current_level:
            data = {}
            for model_field in model_fields:
                if not hasattr(item, model_field):
                    continue
                value = getattr(item, model_field)
                if model_field == 'permission':
                    value = ','.join(value)
                elif value is None:
                    value = ''
                data[model_field] = value
            data['parent_id'] = parent_db_id
            data['menu_key'] = uuid4().hex  # Consistent UUID4
            to_create.append(Menu(**data))

        with transaction.atomic():
            Menu.objects.bulk_create(to_create, batch_size=100)
            created_items = list(Menu.objects.filter(
                menu_key__in=[item.menu_key for item in to_create]
            ))

        id_mapping = {
            src.id: db.id
            for src, db in zip(current_level, created_items)
        }

        for src, db in zip(current_level, created_items):
            src.db_id = db.id
            for child in menu_items:
                if child.parent_id == src.id:
                    child.parent_id = id_mapping[src.id]

        for item in current_level:
            cls._insert_items(menu_items=menu_items, parent_db_id=item.db_id)

    @classmethod
    def _commit_menus_to_db(cls, menu_items: list[MenuItem], app_label: str) -> bool:
        """
        Persist a flat list of MenuItem instances to the database, respecting hierarchy.

        This method:
        - Clears existing Menu entries.
        - Inserts root menus and their descendants recursively.
        - Updates each MenuItem's db_id with the actual database ID.

        Args:
            menu_items (list[MenuItem]): The flat list of menu items to persist.

        Returns:
            bool: True if menus were persisted, False if input is empty.
        """
        if not menu_items:
            return False

        with transaction.atomic():
            if app_label == MenuSyncMode.SYNC_ALL:
                # Clear existing menu records before insertion
                Menu.objects.all().delete()
            else:
                Menu.objects.filter(app_label=app_label).delete()

            # Start inserting from root nodes (parent_db_id=None)
            cls._insert_items(menu_items=menu_items, parent_db_id=None)

        return True

    @classmethod
    def synchronize_menu(cls, app_label: str):
        """
        Synchronize and persist all custom admin menus defined in installed apps.
        """
        # Filter out system apps (e.g., starting with 'django.')
        if app_label != MenuSyncMode.SYNC_ALL and app_label not in cls.valid_app_labels:
            raise AdminMenuImportError(f"Invalid app_label '{app_label}', must be one of installed apps.")

        # Collects and parses menus from apps.
        sync_menus = cls._get_sync_menus_all() if app_label == MenuSyncMode.SYNC_ALL else cls._get_sync_menus(app_label=app_label)

        # Sanitizes parent-child relationships.
        clear_menus = cls._sanitize_menu(menu_items=sync_menus)

        # Persists the final menu structure to the database.
        cls._commit_menus_to_db(menu_items=clear_menus, app_label=app_label)


class AdminMenu:
    """
    AdminMenu assembles MenuItems from multiple sources,
    merges them, builds hierarchical tree and returns final menu structure.
    """

    @staticmethod
    def _load_from_database() -> list[MenuItem]:
        """
        Fetch active menu items from database and convert to MenuItem.
        """
        menu_data = Menu.objects.filter(is_active=True)

        menu_items = []
        for menu in menu_data:
            item = MenuItem.build_node(menu)
            item.source = MenuSource.DATABASE
            menu_items.append(item)
        return menu_items

    @staticmethod
    def _load_from_app_list(app_list: list[dict]) -> list[MenuItem]:
        """
        Convert Django admin app_list data to a flat list of MenuItem objects.

        Since the 'auth' module requires customized display titles, they are hardcoded here.
        """

        menu_items = []

        for app in app_list:
            # Top-level menu (application)
            app_label = app.get('app_label')
            app_item = MenuItem(
                id=app.get('app_label'),
                title='Authentication and Authorization' if app_label == 'auth' else app.get('name', ''),
                url=app.get('app_url'),
                icon=constants.AUTH,
                app_label=app_label,
                source=MenuSource.APP_LIST,
                sort_order=1
            )
            menu_items.append(app_item)

            # Process models under the application
            for model in app.get('models', []):
                object_name = model.get('object_name')
                model_item = MenuItem(
                    id=object_name,
                    parent_id=app_item.id,
                    title=object_name.lower() if app_label == 'auth' else model.get('name', ''),
                    url=model.get('admin_url'),
                    app_label=app_label,
                    source=MenuSource.APP_LIST,
                )
                menu_items.append(model_item)

        return menu_items

    @staticmethod
    def _merge_items(db_menus: list[MenuItem], app_list_menus: list[MenuItem]) -> list[MenuItem]:
        """
        Merge two lists of MenuItem objects with database items taking priority.

        Rules:
            - If a top-level app_list menu has the same app_label as a database menu, discard it.
            - If a child menu from app_list belongs to a known app_label in the database menus,
              update its parent_id to the corresponding database menu's id.
            - Append all valid items into the merged result.

        Args:
            db_menus (list[MenuItem]): Menus loaded from the database.
            app_list_menus (list[MenuItem]): Menus generated from app_list sources.

        Returns:
            list[MenuItem]: Combined menu list for display, with conflicts resolved.
        """
        merged_items: list[MenuItem] = list(db_menus)

        # Build a mapping {app_label: id} for all database top-level menus
        app_label_to_db_id = {
            item.app_label: item.id for item in db_menus if item.parent_id is None
        }

        for app_menu_item in app_list_menus:
            if app_menu_item.parent_id is None:
                # Skip top-level app_list menus if a database menu with the same app_label exists
                if app_menu_item.app_label in app_label_to_db_id:
                    continue
                else:
                    merged_items.append(app_menu_item)
            else:
                # For child menus, if their parent exists in database, remap parent_id to database id
                if app_menu_item.parent_id in app_label_to_db_id:
                    app_menu_item.parent_id = app_label_to_db_id[app_menu_item.parent_id]
                merged_items.append(app_menu_item)

        return merged_items

    @staticmethod
    def filter_by_permissions(menu_tree: list[MenuItem], permissions: list[str]) -> list[MenuItem]:
        # TODO 做权限过滤部分
        return menu_tree

    @classmethod
    def get_menu(cls, app_list: list[dict]) -> list[MenuItem]:
        """ Get final admin menu. """
        #  Load menu from database
        db_items = cls._load_from_database()

        # Load menu from app_list
        app_items = cls._load_from_app_list(app_list=app_list)

        # Merge two sources (db priority)
        merged_items = cls._merge_items(db_menus=db_items, app_list_menus=app_items)

        # Build hierarchical tree
        return MenuItem.build_tree(merged_items, sort_key='sort_order')
