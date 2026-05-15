#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application configuration for Pinmok admin.

Description:
  This module handles initialization of the Pinmok admin site.
  It only registers Django's built-in models (User, Group).
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from django.apps import AppConfig
from django.contrib import admin
from django.contrib.admin import autodiscover
from django.utils.module_loading import autodiscover_modules

from pinmok.core.sites import site


class PadminConfig(AppConfig):
    name = 'pinmok.padmin'
    verbose_name = 'Pinmok Admin'

    def ready(self):
        # Automatically discover models registered on admin and register them on Pinmok site.
        self._pinmok_autodiscover_and_register()
        autodiscover_modules('datasource')

        # Import signals module to trigger signal handler registration via @receiver decorators.
        import pinmok.padmin.signals  # noqa: F401

    @staticmethod
    def _pinmok_autodiscover_and_register():
        """
        Automatically discover all app admin.py files and convert their
        ModelAdmin classes to Pinmok-enabled versions.

        The process ensures that all user-defined ModelAdmin classes
        automatically benefit from Pinmok enhancements without requiring
        any code changes from the user.

        Note:
            This function should be called from AppConfig.ready() to ensure
            all apps are properly initialized before processing.
        """

        # Step 1: Trigger Django's autodiscover to load all admin.py files
        autodiscover()

        # Step 2-5: Process all registered models
        # Use list() to avoid dictionary modification during iteration
        from pinmok.padmin.options import PinmokModelAdmin, PinmokModelAdminMixin
        for model, admin_class in list(admin.site._registry.items()):
            # Skip models that are already registered in Pinmok_site
            # (e.g., User and Group which have custom implementations)
            if site.is_registered(model):
                continue

            if issubclass(admin_class.__class__, (PinmokModelAdmin, PinmokModelAdminMixin)):
                continue

            # Step 3: Dynamically create a Pinmok-enabled admin class
            # Use a factory approach to ensure proper MRO (method resolution order)
            class _PinmokAdmin(PinmokModelAdminMixin, admin_class.__class__):
                """Dynamically created Pinmok admin class."""
                pass

            # Preserve original class metadata for debugging and introspection
            _PinmokAdmin.__name__ = f'Pinmok{admin_class.__class__.__name__}'
            _PinmokAdmin.__module__ = admin_class.__module__

            # Step 4: Register the converted class with the Pinmok site
            site.register(model, _PinmokAdmin)

            # Step 5: Unregister from Django's default admin site
            admin.site.unregister(model)
