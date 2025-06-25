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
from .menus import AdminMenuManager


def site_info(request):
    admin_menu = AdminMenuManager.get_admin_menu(request)
    return {
        'admin_menu': admin_menu
    }
