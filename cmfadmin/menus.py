#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menus module

Description:
  Backend Menu Management
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-11
"""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpRequest

from cmfadmin import constants
from cmfadmin import site
from cmfadmin.enums import MenuPermissions, ConfigCategory
from cmfadmin.service.menu import MenuSynchronizer, AdminMenu, MenuItem

ADMIN_MENU = [
    {
        'title': 'Site Settings',
        'icon': 'tabler-setting',
        'sort_order': 0,
        'permission': ['site.view_menu'],
        'children': [
            {
                'title': ConfigCategory.SITE.label,
                'url': '/admin/cmfadmin/site/',
                'sort_order': 100,
                'permission': ['site.site.view_menu'],
            }, {
                'title': ConfigCategory.EMAIL.label,
                'url': '/admin/cmfadmin/email',
                'sort_order': 200,
                'permission': ['site.email.view_menu'],
            }, {
                'title': ConfigCategory.SYSTEM.label,
                'url': '/admin/cmfadmin/system',
                'sort_order': 300,
                'permission': ['site.system.view_menu'],
            }, {
                'title': ConfigCategory.ICONS.label,
                'url': '/admin/cmfadmin/icons',
                'sort_order': 400,
                'permission': ['site.icons.view_menu'],
            }, {
                'title': ConfigCategory.UPLOAD.label,
                'url': '/admin/cmfadmin/upload',
                'sort_order': 500,
                'permission': ['site.upload.view_menu'],
            },
        ]
    },
]


class AdminMenuManager:
    @staticmethod
    def _clear_admin_menu_cache():
        """
        Clear the cached admin menu.

        Should be called when menu definitions change (e.g., menu sync or edit).
        """
        cache.delete(constants.ADMIN_ALL_MENU)

    @staticmethod
    def _get_user_permissions(user: User) -> list[str]:
        """
        Map a Django User to a list of menu permissions.

        Returns ALL_PERMISSIONS for superusers.
        Returns actual permission codes for normal users.

        Args:
            user (User): Django user object.

        Returns:
            list[str]: List of permission codes.
        """
        if user.is_superuser:
            return [MenuPermissions.ALL_PERMISSIONS]

        # Normal user permissions: match user's Django permissions
        # You can filter only menu-related permissions if needed
        perms_qs = user.user_permissions.values_list('content_type__app_label', 'codename')
        perms_list = [f"{app}.{codename}" for app, codename in perms_qs]

        # Also include permissions via groups
        group_perms_qs = user.groups.values_list(
            'permissions__content_type__app_label',
            'permissions__codename'
        )
        group_perms_list = [f"{app}.{codename}" for app, codename in group_perms_qs]

        all_perms = set(perms_list) | set(group_perms_list)
        return list(all_perms)

    @staticmethod
    def get_admin_breadcrumb(request: HttpRequest, menu_tree: list[MenuItem]) -> list[dict]:
        """
        Generate breadcrumb path for a given URL from the provided admin menu tree.

        Args:
            request(HttpRequest): The current HTTP request.
            menu_tree(list[MenuItem]): Precomputed admin menu tree.

        Returns:
            list[dict]: Breadcrumb items with 'title' and 'url'.
        """
        path = []
        current_url = request.path

        def search(bread_node: MenuItem, trail: list):
            new_trail = trail + [bread_node]
            if bread_node.url and current_url.startswith(bread_node.url):
                nonlocal path
                if len(new_trail) > len(path):
                    path = new_trail
            for child in bread_node.children:
                search(child, new_trail)

        for item in menu_tree:
            search(item, [])

        breadcrumbs = [{'title': node.title, 'url': node.url} for node in path]
        return breadcrumbs

    @classmethod
    def synchronize_menu(cls, app_label: str, user: User) -> dict:
        """
        Synchronize backend menu data with the database.

        This operation scans for application-defined menus and updates the database accordingly.
        Only superusers are allowed to perform this action.

        Args:
            app_label (str): The app label for which to synchronize menus.
            user (User): The current user performing the operation.

        Raises:
            PermissionError: If the user is not a superuser.
        """

        if not user.is_superuser:
            raise PermissionError('Only superusers are allowed to perform this action.')

        cls._clear_admin_menu_cache()
        return MenuSynchronizer.synchronize_menu(app_label=app_label)

    @classmethod
    def get_admin_menu(cls, request: HttpRequest) -> list[MenuItem]:
        """
        Retrieve the final backend admin menu for the given user.

        This method fetches the cached admin menu (or generates it if missing),
        filters it based on the user's permissions, and returns the result
        as a list of menu dictionaries suitable for template rendering.

        Args:
            request(HttpRequest): The current HTTP request.

        Returns:
            list[dict]: The final filtered admin menu for the user.
        """
        app_list = site.get_app_list(request)
        menu_tree = AdminMenu.get_menu(app_list=app_list)

        permissions = cls._get_user_permissions(user=request.user)
        return AdminMenu.filter_by_permissions(menu_tree=menu_tree, permissions=permissions)
