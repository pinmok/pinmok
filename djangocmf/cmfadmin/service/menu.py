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
from enum import StrEnum

from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext as _

from djangocmf.cmfadmin import constants
from djangocmf.cmfadmin.models import Menu
from djangocmf.core.constants import DEFAULT_SORT_ORDER
from djangocmf.core.menu import MenuNode
from djangocmf.core.sites import site
from djangocmf.core.utils.helper import get_valid_app_labels
from djangocmf.core.utils.tools import to_compact_case


class AdminMenuImportError(Exception):
    """Raised when admin menu import fails."""
    pass


class MenuSource(StrEnum):
    """ Menu data sources """
    DATABASE = 'database'
    APP_LIST = 'app_list'


class MenuSyncMode(StrEnum):
    """Menu sync modes"""
    SYNC_ALL = 'all'


class MenuSynchronizer:
    """
    Menu synchronization service.

    Responsibilities:
    1. Fetch menu definitions from each app's menus.py via the menu() factory.
    2. Resolve url names to actual paths at sync time.
    3. Persist menus into the database.

    Menu items are declared via the menu() factory function in each app's
    menus.py. Parent-child relationships are established via parent_key at
    declaration time, so no post-processing normalization is needed.
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

                # 2. Clear old menus for this app
                cls._clear_app_menus(app)

                # 3. Persist menus
                total_created += cls._insert_items(nodes, parent_db_id=None)

                inserted_menus.extend(nodes)

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
        Fetch menu definitions from an app's menus.py and resolve url names.

        Each MenuNode's url is resolved at sync time:
          - If url starts with '/', it is treated as a literal path and used as-is.
          - Otherwise, it is treated as a Django url name and resolved via reverse().
            If resolution fails, AdminMenuImportError is raised immediately.

        Returns a list of MenuNode instances with app_label and url filled in.
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
                node.app_label = app_label
                # Resolve url name to actual path if not already a path.
                if node.url and not node.url.startswith('/'):
                    try:
                        node.url = reverse(node.url)
                    except NoReverseMatch:
                        raise AdminMenuImportError(
                            f"Cannot reverse url {node.url!r} for menu item {node.id!r} "
                            f"in app '{app_label}'."
                        )
                nodes.append(node)
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
            field: value  # noqa
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
        Insert menu items into the database recursively.

        Processes one level at a time: all nodes whose parent_id matches
        parent_db_id are inserted together via bulk_create, then their
        children are inserted recursively using the newly assigned DB IDs.

        Args:
            menu_nodes: Flat list of all MenuNode instances for the current app.
            parent_db_id: The database PK of the parent menu row, or None for root level.

        Returns:
            int: Total number of menu rows created.
        """
        created_count = 0
        current_level = [item for item in menu_nodes if item.parent_id == parent_db_id]
        if not current_level:
            return 0

        # Step 1: Prepare Menu objects and sync menu_key back to each node.
        to_create = []
        for item in current_level:
            menu_obj = cls._prepare_menu_obj(item, parent_db_id)
            item.menu_key = menu_obj.menu_key  # sync back so created_map lookup works
            to_create.append(menu_obj)

        # Step 2: Insert Menu objects
        Menu.objects.bulk_create(to_create, batch_size=100)
        created_items = list(Menu.objects.filter(menu_key__in=[m.menu_key for m in to_create]))
        created_count += len(created_items)

        # Step 3: Build mapping from menu_key to inserted DB row.
        created_map = {m.menu_key: m for m in created_items}
        for src in current_level:
            db = created_map[src.menu_key]
            src.db_id = db.id
            # Remap children's parent_id from the node's logical id to the DB PK.
            for child in menu_nodes:
                if child.parent_id == src.id:
                    child.parent_id = db.id

        # Step 4: Recursively insert child nodes.
        for item in current_level:
            created_count += cls._insert_items(menu_nodes=menu_nodes, parent_db_id=item.db_id)

        return created_count

    @staticmethod
    def _clear_app_menus(app_label: str):
        """
        Clear all menu rows for a single app before re-synchronizing.

        Cascade delete handles child rows automatically via the ForeignKey
        on Menu.parent.
        """
        Menu.objects.filter(app_label=app_label).delete()


class AdminMenuService:
    """
    Assembles menu nodes from multiple sources, merges them, applies permission
    filtering, builds a hierarchical tree, and returns the final menu structure.

    This class is the data layer for menu rendering. For request-level concerns
    (caching, permission gating on sync), use AdminMenuManager.
    """

    @staticmethod
    def _load_from_database() -> list[MenuNode]:
        """
        Fetch menu items from the database and convert to MenuNode instances.

        The permissions field is stored as a JSON list in the database and is
        mapped directly onto MenuNode.permissions by build_node.
        """
        menu_data = Menu.objects.all()
        menu_nodes: list[MenuNode] = []

        for menu in menu_data:
            node = MenuNode.build_node(menu)
            node.title = _(node.title)
            node.source = MenuSource.DATABASE
            # Ensure permissions is always a list regardless of DB value.
            if not isinstance(node.permissions, list):
                node.permissions = []
            menu_nodes.append(node)

        return menu_nodes

    @staticmethod
    def _load_from_app_list(app_list: list[dict]) -> list[MenuNode]:
        """
        Convert Django admin app_list data to a flat list of MenuNode objects.

        The icon for each app is read from its AppConfig.icon attribute.
        Since 'auth' is a built-in Django app whose AppConfig cannot be
        customised, its icon is taken from constants.AUTH_APP_ICON instead.
        All other apps fall back to constants.DEFAULT_APP_ICON if no icon
        attribute is defined on their AppConfig.
        """
        menu_nodes: list[MenuNode] = []

        for app in app_list:
            app_label = app.get('app_label', '')
            app_config = apps.get_app_config(app_label)

            # Resolve icon: auth is a special case, others read from AppConfig.
            if app_label == 'auth':
                icon = constants.AUTH_APP_ICON
            else:
                icon = getattr(app_config, 'icon', constants.DEFAULT_APP_ICON)

            app_item = MenuNode(
                id=app_label,
                title=app_config.verbose_name,
                url=app.get('app_url'),
                icon=icon,
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

            for model in app.get('models', []):
                object_name = model.get('object_name')
                model_admin = site.get_model_admin(model['model'])
                sort_order = getattr(model_admin, 'menu_order', DEFAULT_SORT_ORDER)

                model_item = MenuNode(
                    id=object_name,
                    parent_id=app_label,
                    title=model.get('name') or object_name,
                    url=model.get('admin_url'),
                    app_label=app_label,
                    source=MenuSource.APP_LIST,
                    sort_order=sort_order,
                )
                menu_nodes.append(model_item)

        return menu_nodes

    @staticmethod
    def _filter_by_permissions(menu_nodes: list[MenuNode], user: AbstractUser) -> list[MenuNode]:
        """
        Filter menu nodes according to user's permissions.

        Two-pass algorithm:
          Pass 1 — collect nodes that fail their own permission check.
          Pass 2 — propagate denial to all descendants, repeat until stable.

        This ensures correct filtering regardless of node ordering in the list,
        and that removing a parent always removes all its children too.
        """
        if not user.is_authenticated:
            return []

        if user.is_superuser:
            return menu_nodes

        # Pass 1: collect nodes whose own permissions are insufficient.
        denied_ids: set = set()
        for node in menu_nodes:
            if node.permissions and not any(user.has_perm(perm) for perm in node.permissions):
                denied_ids.add(node.id)

        # Pass 2: propagate denial to descendants, repeat until stable.
        while True:
            new_denied = {
                node.id for node in menu_nodes
                if node.id not in denied_ids and node.parent_id in denied_ids
            }
            if not new_denied:
                break
            denied_ids |= new_denied

        return [node for node in menu_nodes if node.id not in denied_ids]

    @classmethod
    def get_merged_nodes(cls, menu_nodes: list[MenuNode], app_list_menu_nodes: list[MenuNode]) -> list[MenuNode]:
        """
        Merge two lists of MenuNode objects with database items taking priority.

        Rules:
            - If a top-level app_list menu has the same app_label as a database menu,
              attach it under the database menu instead of adding it as a root.
            - If a child menu from app_list belongs to a known app_label in the database
              menus, remap its parent_id to the corresponding database menu's id.
            - All valid items are appended into the merged result.

        Returns:
            list[MenuNode]: Combined menu list for display, with conflicts resolved.
        """
        merged_nodes: list[MenuNode] = list(menu_nodes)

        # Build a mapping {app_label: first_root_id} for all database top-level menus.
        app_label_to_db_id = {}
        for item in menu_nodes:
            if item.parent_id is None and item.app_label not in app_label_to_db_id:
                app_label_to_db_id[item.app_label] = item.id

        for app_menu_item in app_list_menu_nodes:
            if app_menu_item.parent_id is None:
                if app_menu_item.app_label in app_label_to_db_id:
                    # Attach under the existing database root for this app.
                    app_menu_item.parent_id = app_label_to_db_id[app_menu_item.app_label]
                else:
                    merged_nodes.append(app_menu_item)
            else:
                if app_menu_item.parent_id in app_label_to_db_id:
                    app_menu_item.parent_id = app_label_to_db_id[app_menu_item.parent_id]
                merged_nodes.append(app_menu_item)

        return merged_nodes

    # AdminMenuService 里加
    @classmethod
    def get_db_menus(cls) -> list[MenuNode]:
        """Return database menus, using cache if available."""
        version = cache.get(constants.ADMIN_MENU_CACHE_VERSION, 1)
        cache_key = f"{constants.ADMIN_ALL_MENU}_v{version}"
        db_menus = cache.get(cache_key)
        if db_menus is None:
            db_menus = cls._load_from_database()
            cache.set(cache_key, db_menus, timeout=60 * 60)
        return db_menus

    @classmethod
    def get_menu(cls, app_list: list[dict], user: AbstractUser, db_menus=None) -> list[MenuNode]:
        """
        Assemble, filter, merge and return the final admin menu tree.

        Steps:
          1. Load database menus.
          2. Filter by user permissions.
          3. Load app_list menus.
          4. Merge both sources (database takes priority).
          5. Build and return the hierarchical tree.
        """
        db_menus = db_menus or cls._load_from_database()
        menu_nodes = cls._filter_by_permissions(db_menus, user)
        app_list_nodes = cls._load_from_app_list(app_list=app_list)
        merged_nodes = cls.get_merged_nodes(menu_nodes, app_list_nodes)
        return MenuNode.build_tree(merged_nodes, sort_key='sort_order')


# ===========================================================================
# AdminMenuManager
# ===========================================================================

class AdminMenuManager:
    """
    Request-level facade for the admin menu system.

    Responsibilities:
      - Per-user menu caching with version-based invalidation.
      - Breadcrumb generation from the menu tree.
      - Menu synchronization with superuser permission gating.

    Callers (views, context processors) should only use this class.
    AdminMenuService and MenuSynchronizer are implementation details.
    """

    # -----------------------------------------------------------------------
    # Cache helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_cache_version() -> int:
        return cache.get(constants.ADMIN_MENU_CACHE_VERSION, 1)

    @staticmethod
    def clear_admin_menu_cache() -> None:
        """
        Invalidate all per-user menu caches by incrementing the global version.

        All existing per-user cache entries become stale immediately without
        requiring pattern-based deletion, which is not supported by all cache
        backends.
        """
        version = cache.get(constants.ADMIN_MENU_CACHE_VERSION, 1)
        cache.set(constants.ADMIN_MENU_CACHE_VERSION, version + 1)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @classmethod
    def get_admin_menu(cls, request: HttpRequest, app_list: list | None = None) -> list[MenuNode]:
        """
        Retrieve the final backend admin menu for the current user.

        The result is cached per user per cache version. Invalidate by calling
        _clear_admin_menu_cache() (e.g., after menu sync or permission change).

        Args:
            request: The current HTTP request.
            app_list: Use provided app_list to avoid redundant get_app_list() call

        Returns:
            list[MenuNode]: Hierarchical menu tree ready for template rendering.
        """
        if app_list is None:
            app_list = site.get_app_list(request)
        db_menus = AdminMenuService.get_db_menus()
        return AdminMenuService.get_menu(app_list=app_list, user=request.user, db_menus=db_menus)

    @classmethod
    def synchronize_menu(cls, app_label: str, user: AbstractUser) -> dict:
        """
        Synchronize backend menu data with the database.

        Only superusers are allowed to perform this action. The per-user menu
        cache is invalidated after a successful sync.

        Args:
            app_label: The app label to sync, or MenuSyncMode.SYNC_ALL for all apps.
            user: The current user performing the operation.

        Raises:
            PermissionDenied: If the user is not a superuser.
        """
        if not user.is_superuser:
            raise PermissionDenied('Only superusers are allowed to perform this action.')

        result = MenuSynchronizer.synchronize_menu(app_label=app_label)
        cls.clear_admin_menu_cache()
        return result

    @staticmethod
    def get_admin_breadcrumb(request: HttpRequest, menu_tree: list[MenuNode]) -> list[dict]:
        """
        Generate breadcrumb path for the current URL from the menu tree.
        Traverses depth-first and returns the longest matching trail.
        """
        current_url = request.path.rstrip('/')

        def search(node: MenuNode, trail: list[MenuNode]) -> list[MenuNode]:
            new_trail = trail + [node]
            best = []

            # Check if this node matches current URL
            if node.url:
                node_url = node.url.rstrip('/')
                if current_url == node_url or current_url.startswith(f"{node_url}/"):
                    best = new_trail

            # Recurse into children, keep the longest match
            for child in node.children:
                candidate = search(child, new_trail)
                if len(candidate) > len(best):
                    best = candidate

            return best

        path = []
        for item in menu_tree:
            result = search(item, [])
            if len(result) > len(path):
                path = result

        return [
            {'title': node.title, 'url': node.url, 'is_current': i == len(path) - 1}
            for i, node in enumerate(path)
        ]
