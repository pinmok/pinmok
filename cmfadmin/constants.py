#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
constants module

Description:
  Global Constants
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
# Variable name menus should be defined under in menus.py files
ADMIN_MENU_VAR_NAME = "ADMIN_MENU"

# CMF menus settings variables
ADMIN_MENU_SETTING_KEY = 'CMF_ADMIN_MENU'
MENU_SETTINGS_KEY = 'MENU_IMPORT_PATHS'
PATH_KEY = 'path'
APP_LABEL_KEY = 'app_label'

# Cache keys
ADMIN_ALL_MENU = 'admin_all_menu'
SITE_INFO = 'site_info'
SYS_INFO = 'sys_info'

# Auth menu icon constant
AUTH = 'tabler-user-shield'

# Custom EmailBackend for overriding email sending configuration
CMF_EMAIL_BACKEND = 'cmfadmin.backends.EmailBackend'

DEFAULT_SORT_ORDER = 10000

# custom sprite.svg file path
CUSTOM_SPRITE_FILE = 'svg/custom_sprite.svg'
