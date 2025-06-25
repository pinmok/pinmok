#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin module

Description:
  Core admin site definition.

  core_site is the primary admin site of DjangoCMF, replacing Django's default admin.site.
  It centralizes the registration of core system models, plugins, and pluggable apps.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import DefaultAdminSite
from django.core.cache import cache
from django.urls import path
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy

from . import urls
from .options import CMFModelAdmin
from .utils.helper import get_system_info, get_disk_info


class CMFAdminSite(AdminSite):
    """
    Custom admin site class extending Django's AdminSite to provide
    enhanced features tailored for the CMF (Content Management Framework) system.

    This class manages the registration and display of models with
    customized admin interfaces (CMFModelAdmin), supports dynamic menu
    construction, permission checks, and integrates additional CMS-specific
    functionalities.
    """
    site_title = settings.CMF_NAME
    site_header = format_lazy('{} {}', settings.CMF_NAME, gettext_lazy('Administration'))
    index_title = format_lazy('{} {}', settings.CMF_NAME, gettext_lazy('Site administration'))

    index_template = "admin/index.html"

    def __init__(self, name='admin'):
        super().__init__(name=name)

        # Copy registered models from default admin site
        self._registry.update(admin.site._registry)

    def register(self, model_or_iterable, admin_class=..., **options):
        """
        Register a model or iterable with a CMFModelAdmin-based admin class, wrapping the given admin_class if needed.
        """
        if admin_class is None:
            admin_class = CMFModelAdmin
        else:
            assert issubclass(admin_class, CMFModelAdmin), \
                f"{admin_class.__name__} must inherit from CMFModelAdmin"
        super().register(model_or_iterable, admin_class=admin_class, **options)

    def get_urls(self):
        """
        Appends custom admin views to the default admin URL patterns
        """
        custom_urls = []
        for route, view, name in getattr(urls, 'cmfadmin_urls', []):
            # 确保末尾有 /
            if not route.endswith('/'):
                route = f'{route}/'
            custom_urls.append(path(route, self.admin_view(view), name=name))
        return custom_urls + super().get_urls()

    def index(self, request, extra_context=None):
        """
        Render the admin site's index page with additional system info in the context.
        """
        extra_context = extra_context or {}

        # Add custom context variables
        extra_context.update({
            'sys_info': cache.get_or_set('sys_info', get_system_info, timeout=3600 * 24 * 30),
            'disk_info': cache.get_or_set('disk_info', get_disk_info, timeout=3600)
        })

        # Call the parent class's index method, passing the updated context to render the admin index page
        return super().index(request, extra_context)


class DefaultCmfAdminSite(DefaultAdminSite):
    """
    Initialize the default CMF admin site by wrapping an instance of CMFAdminSite.
    """

    def _setup(self):
        self._wrapped = CMFAdminSite()


# Instantiate the custom admin site with a unique name for URL reversing and namespace distinction
site = DefaultCmfAdminSite()
