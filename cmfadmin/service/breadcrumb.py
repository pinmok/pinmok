#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
breadcrumb module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-29
"""
from django.http import HttpRequest

from cmfadmin.menus import AdminMenuManager
from cmfadmin.service.menu import MenuItem


class BreadCrumb:
    """
    Service for generating breadcrumbs for admin pages.
    """

    @staticmethod
    def get_admin_breadcrumb(request: HttpRequest) -> list[dict]:
        """
        Generate breadcrumb path for a given URL from the admin menu tree.

        Args:
           request(HttpRequest): The current HTTP request.

        Returns:
            list[dict]: Breadcrumb items with 'title' and 'url'.
        """
        path = []
        current_url = request.path
        menu_tree = AdminMenuManager.get_admin_menu(request)

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

        breadcrumbs = []
        for node in path:
            breadcrumbs.append({
                'title': node.title,
                'url': node.url
            })

        return breadcrumbs
