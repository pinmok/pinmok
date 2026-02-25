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


class CmfadminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'djangocmf.cmfadmin'
    verbose_name = 'DjangoCMF'

    def ready(self):
        """
        Register Django's built-in auth models with CMF admin site.
        """
        from djangocmf.core import site
        from django.contrib.auth.models import User, Group
        from djangocmf.cmfadmin.admin import CmfUserAdmin, CmfGroupAdmin

        # Register Django's built-in auth models
        if not site.is_registered(User):
            site.register(User, CmfUserAdmin)
        if not site.is_registered(Group):
            site.register(Group, CmfGroupAdmin)
