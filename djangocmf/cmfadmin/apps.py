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

default_app_config = 'djangocmf.core.apps.CmfAdminConfig'


class CmfadminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'djangocmf.cmfadmin'
    verbose_name = 'DjangoCMF'
