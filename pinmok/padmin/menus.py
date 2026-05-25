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

from pinmok.core import menu
from pinmok.padmin.enums import ConfigCategory

# Define Pinmok Admin menu
admin_menu = [
    menu('config', title='Site Settings', icon='tabler-settings', sort_order=0),
    menu(
        ConfigCategory.ICONS.value,
        title=ConfigCategory.ICONS.label,
        url='admin:padmin:icons_manage',
        parent_key='config',
        sort_order=4000,
        permissions=["padmin.view_icon", "padmin.change_icon"]
    ),
    menu(
        'theme',
        title='Template Management',
        url='admin:padmin:theme_list',
        parent_key='config',
        sort_order=8000,
        permissions=["padmin.view_theme"]
    )
]
