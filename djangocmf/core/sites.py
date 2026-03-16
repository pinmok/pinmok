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
import warnings

from django.apps import apps
from django.conf import settings
from django.contrib.admin import AdminSite
from django.core.cache import cache
from django.template.response import TemplateResponse
from django.urls import path, include, URLPattern, URLResolver
from django.views.i18n import JavaScriptCatalog

import djangocmf
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
    site_header = 'DjangoCMF'
    site_title = 'DjangoCMF Admin'

    @property
    def password_change_form(self):
        """
        Originally a class attribute, converted to a property to avoid
        AppRegistryNotReady error caused by early import of AdminChangePasswordForm,
        which transitively imports models before Django's app registry is ready.
        """
        from djangocmf.cmfadmin.forms.forms import CMFAdminPasswordChangeForm
        return CMFAdminPasswordChangeForm

    def admin_view(self, view, cacheable=False):
        """
        Wrap an admin view to inject shared context if not already present.

        Overrides the default admin_view to ensure every TemplateResponse
        contains the shared context data (e.g. admin_menu) provided by
        each_context(). If the response is not a TemplateResponse, or the
        context already contains 'admin_menu', it is left untouched.

        Args:
            view (callable): The view function to wrap.
            cacheable (bool): Whether the view's response may be cached.
                              Passed through to the parent implementation.

        Returns:
            callable: The wrapped view.
        """

        def inner(request, *args, **kwargs):
            response = view(request, *args, **kwargs)
            if isinstance(response, TemplateResponse) and 'admin_menu' not in response.context_data:
                response.context_data.update(self.each_context(request))
            return response

        return super().admin_view(inner, cacheable=cacheable)

    def i18n_javascript(self, request, extra_context=None):
        """
        Display the i18n JavaScript for both Django admin and project apps.
        """
        # Set package to None to use the `po` files of all apps
        return JavaScriptCatalog.as_view(packages=None)(request)

    def get_urls(self):
        """
        Build URL patterns for the admin site.

        This method scans all installed apps for a module-level variable
        named `admin_urlpatterns`. If found, each URLPattern will be wrapped
        with `self.admin_view()` to enforce admin permissions and then
        registered into the admin site's URL configuration.

        This design allows apps to contribute admin URLs without directly
        coupling to the admin site implementation.

        Returns:
            list: Complete URL patterns for the admin site
        """
        from djangocmf.cmfadmin.views import license_page, sync_menu, UserProfile

        # Some CMF admin URLs without 'admin' prefix
        urlpatterns: list[URLPattern | URLResolver] = [
            path('license/', self.admin_view(license_page), name='license_page'),
            path('sync-menu/', self.admin_view(sync_menu), name='sync_menu'),
            path('profile/', self.admin_view(UserProfile.as_view()), name='profile')
        ]

        # Scan apps for admin URL contributions
        for app in apps.get_app_configs():
            try:
                mod = importlib.import_module(f"{app.name}.urls")
            except ModuleNotFoundError:
                # App doesn't have urls.py, skip it
                continue

            # Look for admin_urlpatterns
            admin_urls = getattr(mod, 'admin_urlpatterns', None)
            if not admin_urls:
                continue

            # Validate that admin_urls is iterable
            if not hasattr(admin_urls, '__iter__'):
                warnings.warn(
                    f"App '{app.label}' has admin_urlpatterns but it's not iterable. Skipping.",
                    UserWarning
                )
                continue

            # Wrap each URL pattern with admin_view() for permission checking
            wrapped_urls = []
            for url_pattern in admin_urls:
                try:
                    if isinstance(url_pattern, URLPattern):
                        # Create a new URLPattern with wrapped callback
                        # Don't modify the original url_pattern object
                        wrapped_pattern = URLPattern(
                            pattern=url_pattern.pattern,
                            callback=self.admin_view(url_pattern.callback),
                            default_args=url_pattern.default_args,
                            name=url_pattern.name
                        )
                        wrapped_urls.append(wrapped_pattern)
                    elif isinstance(url_pattern, URLResolver):
                        # URLResolver (include) can be added directly
                        # The admin_view wrapping should be done in the included URLs
                        wrapped_urls.append(url_pattern)
                    else:
                        warnings.warn(
                            f"App '{app.label}' has an unrecognized URL pattern type: {type(url_pattern)}. Skipping.",
                            UserWarning
                        )
                except Exception as e:
                    warnings.warn(
                        f"Error processing URL pattern in app '{app.label}': {e}. Skipping.",
                        UserWarning
                    )
                    continue

            # Include wrapped URLs under app namespace
            if wrapped_urls:
                urlpatterns.append(path(f"{app.label}/", include((wrapped_urls, app.label))))

        # Append Django's default admin URLs
        return urlpatterns + super().get_urls()

    def each_context(self, request):
        """
        Extend the default admin context with CMF-specific data,
        including menu tree, breadcrumbs, and global settings.
        """
        from djangocmf.cmfadmin.service.menu import AdminMenuManager

        context = super().each_context(request)

        menu_tree = AdminMenuManager.get_admin_menu(request, app_list=context['available_apps'])
        breadcrumbs = AdminMenuManager.get_admin_breadcrumb(request, menu_tree)
        context.update({
            'SOFTWARE_NAME': djangocmf.__name__,
            'USE_I18N': settings.USE_I18N,
            'admin_menu': menu_tree,
            'admin_breadcrumbs': breadcrumbs
        })
        return context

    def index(self, request, extra_context=None):
        """
        Render the admin site's index page with system monitoring information.

        Args:
            request: HttpRequest object
            extra_context: Additional context dict (optional)

        Returns:
            HttpResponse: Rendered admin index page
        """
        extra_context = extra_context or {}

        # Add custom context variables
        extra_context.update({
            'index_title': self.index_title,
            # System info: cached for 24 hours (CPU, memory, OS version)
            'sys_info': cache.get_or_set('cmf_sys_info', get_system_info, timeout=3600 * 24),
            # Disk info: cached for 1 hour (disk usage can change frequently)
            'disk_info': cache.get_or_set('cmf_disk_info', get_disk_info, timeout=3600)
        })

        # Render the index page with enhanced context
        return super().index(request, extra_context)


# Instantiate the custom admin site with a unique name for URL reversing and namespace distinction
site = DjangoCmfAdminSite()
