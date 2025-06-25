#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apps module

Description:
  apps module of CMF
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CmfAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cmfadmin'
    verbose_name = _('CMF Admin')
