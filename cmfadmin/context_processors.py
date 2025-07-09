#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_processor module

Description:
  The context processor of CMF
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-15
"""
from cmfadmin import site
from cmfadmin.menus import AdminMenuManager
from cmfadmin.service.breadcrumb import BreadCrumb


def admin_context(request):
    menu_tree = AdminMenuManager.get_admin_menu(request)
    breadcrumbs = BreadCrumb.get_admin_breadcrumb(request)

    return {
        'site_header': site.site_header,
        'site_title': site.site_title,
        'admin_menu': menu_tree,
        'admin_breadcrumbs': breadcrumbs
    }
