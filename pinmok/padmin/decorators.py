#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decorators module

Description:

Author:
  惠达浪 <crazys@126.com>
Created:
  2026/1/24
"""

from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite

from pinmok.core.sites import site as padmin_site


def register(*models, site=None):
    """
    Decorator to register a model or models with a PinmokAdminSite-based admin class.
    """

    def _wrapper(admin_class):
        if not models:
            raise ValueError("At least one model must be passed to register.")

        admin_site = site or padmin_site

        if not isinstance(admin_site, AdminSite):
            raise ValueError("site must subclass AdminSite")

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError("Wrapped class must subclass ModelAdmin.")

        admin_site.register(models, admin_class=admin_class)

        return admin_class

    return _wrapper
