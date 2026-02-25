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


def register(*models, site=None):
    """
    Decorator to register a model or models with a CMFAdminSite-based admin class.
    """
    from django.contrib.admin import ModelAdmin
    from django.contrib.admin.sites import AdminSite
    from djangocmf.core.sites import site as cmfadmin_site

    def _wrapper(admin_class):
        if not models:
            raise ValueError("At least one model must be passed to register.")

        admin_site = site or cmfadmin_site

        if not isinstance(admin_site, AdminSite):
            raise ValueError("site must subclass AdminSite")

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError("Wrapped class must subclass ModelAdmin.")

        admin_site.register(models, admin_class=admin_class)

        return admin_class

    return _wrapper
