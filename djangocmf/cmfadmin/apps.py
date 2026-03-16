#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application configuration for DjangoCMF admin.

Description:
  This module handles initialization of the CMF admin site.
  It only registers Django's built-in models (User, Group).
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from django.apps import AppConfig

from djangocmf.cmfadmin.utils.helper import cmf_autodiscover_and_register


class CmfadminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'djangocmf.cmfadmin'
    verbose_name = 'DjangoCMF'

    def ready(self):
        # Automatically discover models registered on admin and register them on DjangoCMF site.
        cmf_autodiscover_and_register()

        # Import signals module to trigger signal handler registration via @receiver decorators.
        import djangocmf.cmfadmin.signals  # noqa: F401
