#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMF settings module

Description:
  CMF-specific configuration settings.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from . import name, version

CMF_NAME = name
CMF_VERSION = version

CMF_ADMIN_MENU = {
    'MENU_IMPORT_PATHS': [
        # Example: {'path': 'apps.blog.menus.CUSTOM_MENU', 'app_label': 'blog'}
        {'path': 'apps.portal.menus.export_menu', 'app_label': 'portal'},
    ]
}
