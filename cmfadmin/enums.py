#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enums module

Description:
  Centralized module for all project-wide enumeration classes.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-15
"""
from enum import StrEnum

from django.db import models


# Menu sync modes
class MenuSyncMode(StrEnum):
    SYNC_ALL = 'all'


# Menu permission constants
class MenuPermissions(StrEnum):
    ALL_PERMISSIONS = '*'


# Menu data sources
class MenuSource(StrEnum):
    DATABASE = 'database'
    APP_LIST = 'app_list'


# Config model enum
class ConfigCategory(models.TextChoices):
    SITE = 'site', 'Site Information'
    EMAIL = 'email', 'Email Settings'
    LINKS = 'links', 'External Links'
    NAV = 'nav', 'Navigation Management'
    TEMPLATE = 'template', 'Template Management'
    SYSTEM = 'system', 'System Settings'
    ICONS = 'icons', 'Icons Management'


# Config model enum
class ConfigType(models.TextChoices):
    TEXT = 'text'
    TEXTAREA = 'textarea'
    IMAGE = 'image'
    SWITCH = 'switch'
    SELECT = 'select'
    RADIO = 'radio'
    CHECKBOX = 'checkbox'
    RICHTEXT = 'richtext'
    PASSWORD = 'password'
    NUMBER = 'number'
    FILE = 'file'


# Navigation type
class TargetChoices(models.TextChoices):
    SELF = '_self', 'Self Window'
    BLANK = '_blank', 'Blank Window'
