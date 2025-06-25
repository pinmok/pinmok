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
from django.utils.translation import gettext_lazy as _


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
    SITE = 'site', _('Site Information')
    SEO = 'seo', _('SEO Settings')
    CDN = 'cdn', _('CDN Settings')


# Config model enum
class ConfigType(models.TextChoices):
    TEXT = 'text', _('Text')
    TEXTAREA = 'textarea', _('Textarea')
    IMAGE = 'image', _('Image')
    SWITCH = 'switch', _('Switch')
    SELECT = 'select', _('Select')
    RADIO = 'radio', _('Radio')
    CHECKBOX = 'checkbox', _('Checkbox')
    RICHTEXT = 'richtext', _('Rich Text')
    PASSWORD = 'password', _('Password')
    NUMBER = 'number', _('Number')
    FILE = 'file', _('File')
