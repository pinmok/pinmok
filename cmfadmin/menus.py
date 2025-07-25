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
    {'title': 'Site Settings', 'icon': 'tabler-setting', 'sort_order': 0, 'children': [
        {'title': ConfigCategory.SITE.label, 'url': '/admin/cmfadmin/site/', 'sort_order': 100},
        {'title': ConfigCategory.EMAIL.label, 'url': '/admin/cmfadmin/email', 'sort_order': 200},
        {'title': ConfigCategory.SYSTEM.label, 'url': '/admin/cmfadmin/system', 'sort_order': 300},
        {'title': ConfigCategory.ICONS.label, 'url': '/admin/cmfadmin/icons', 'sort_order': 400},
        {'title': ConfigCategory.UPLOAD.label, 'url': '/admin/cmfadmin/upload', 'sort_order': 500},
    ]},
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
    def _get_user_permissions(user: User):
        # TODO 解析用户权限
        return [MenuPermissions.ALL_PERMISSIONS]

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
