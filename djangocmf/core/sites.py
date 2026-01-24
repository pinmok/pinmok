#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin module

Description:
  Core admin site definition.

  core_site is the primary admin site, replacing Django's default admin.site.
  It centralizes the registration of core system models, plugins, and pluggable apps.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
import importlib

from django.apps import apps
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import DefaultAdminSite
from django.core.cache import cache
from django.urls import path, include, URLPattern, URLResolver

from djangocmf.cmfadmin.utils.helper import get_system_info, get_disk_info


class DjangoCmfAdminSite(AdminSite):
    """
    Custom admin site class extending Django's AdminSite to provide
    enhanced features tailored for the CMF (Content Management Framework) system.

    This class manages the registration and display of models with
    customized admin interfaces (CMFModelAdmin), supports dynamic menu
    construction, permission checks, and integrates additional CMS-specific
    functionalities.
    """
    index_template = "admin/index.html"

    def __init__(self, name='admin'):
        super().__init__(name=name)

        # Copy registered models from default admin site
        self._registry.update(admin.site._registry)

    # def register(self, model_or_iterable, admin_class=..., **options):
    #     """
    #     Register a model or iterable with a CMFModelAdmin-based admin class, wrapping the given admin_class if needed.
    #     """
    #     if admin_class is None:
    #         admin_class = DjangoCmfModelAdmin
    #     else:
    #         assert issubclass(admin_class, DjangoCmfModelAdmin), \
    #             f"{admin_class.__name__} must inherit from DjangoCmfModelAdmin"
    #     super().register(model_or_iterable, admin_class=admin_class, **options)

    def get_urls(self):
        """
        Inject admin-only URLs provided by installed apps.

        This method scans all installed apps for a module-level variable
        named `admin_urlpatterns`. If found, each URLPattern will be wrapped
        with `self.admin_view()` to enforce admin permissions and then
        registered into the admin site's URL configuration.

        This design allows apps to contribute admin URLs without directly
        coupling to the admin site implementation.
        """
        from djangocmf.cmfadmin.views import license_page, sync_menu, UserProfile

        urlpatterns: list[URLPattern | URLResolver] = [
            path('license/', self.admin_view(license_page), name='license_page'),
            path('sync-menu/', self.admin_view(sync_menu), name='sync_menu'),
            path('profile/', self.admin_view(UserProfile.as_view()), name='profile')
        ]

        for app in apps.get_app_configs():
            try:
                mod = importlib.import_module(f"{app.name}.urls")
            except ModuleNotFoundError:
                continue

            admin_urls = getattr(mod, 'admin_urlpatterns', None)
            if not admin_urls:
                continue

            wrapped_urls = []
            for url in admin_urls:
                url.callback = self.admin_view(url.callback)
                wrapped_urls.append(url)

            urlpatterns.append(
                path(f"{app.label}/", include((wrapped_urls, app.label)))
            )

        return urlpatterns + super().get_urls()

    def index(self, request, extra_context=None):
        """
        Render the admin site's index page with additional system info in the context.
        """
        extra_context = extra_context or {}

        # Add custom context variables
        extra_context.update({
            'index_title': self.index_title,
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
        self._wrapped = DjangoCmfAdminSite()


# Instantiate the custom admin site with a unique name for URL reversing and namespace distinction
site = DefaultCmfAdminSite()
