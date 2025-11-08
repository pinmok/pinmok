#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin module

Description:
  Core admin site definition.

  core_site is the primary admin site of CrazyCMF, replacing Django's default admin.site.
  It centralizes the registration of core system models, plugins, and pluggable apps.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-07
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import DefaultAdminSite
from django.core.cache import cache
from django.urls import path
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

import djangocmf
from cmfadmin import CMFModelAdmin
from cmfadmin.utils.helper import get_system_info, get_disk_info


class CMFAdminSite(AdminSite):
    """
    Custom admin site class extending Django's AdminSite to provide
    enhanced features tailored for the CMF (Content Management Framework) system.

    This class manages the registration and display of models with
    customized admin interfaces (CMFModelAdmin), supports dynamic menu
    construction, permission checks, and integrates additional CMS-specific
    functionalities.
    """
    site_title = djangocmf.name
    site_header = format_lazy('{} {}', djangocmf.name, _('Administration'))
    index_title = format_lazy('{} {}', djangocmf.name, _('Site administration'))

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
        Override the default get_urls method to inject custom admin-only URLs.

        This method adds extra admin views defined in 'cmfadmin_urls' to the admin site.
        Each view is wrapped with self.admin_view() to apply admin-specific permissions,
        CSRF protection, and exception handling.
        """
        from cmfadmin.views import (
            UserProfile,
            SiteInfoView,
            EmailConfigView,
            SpriteManagerView,
            nav_items_edit,
            NavItemView,
            FileManagementView,
            UploadSettingView,
            UploadFileView,
            sync_menu
        )

        custom_urls = [
            path('sync-menu/', self.admin_view(sync_menu), name='sync_menu'),
            path('profile/', self.admin_view(UserProfile.as_view()), name='profile'),
            path('cmfadmin/site/', self.admin_view(SiteInfoView.as_view()), name='site_config'),
            path('cmfadmin/email/', self.admin_view(EmailConfigView.as_view()), name='email_config'),
            path('cmfadmin/icons/', self.admin_view(SpriteManagerView.as_view()), name='icons_manage'),
            path('cmfadmin/nav/<int:pk>/', self.admin_view(nav_items_edit), name='nav_items_edit'),
            path('cmfadmin/nav/navitem/<int:nav_id>/<int:nav_item_id>/', self.admin_view(NavItemView.as_view()), name='navitem'),
            path('cmfadmin/files/', self.admin_view(FileManagementView.as_view()), name='file_management'),
            path('cmfadmin/upload/', self.admin_view(UploadSettingView.as_view()), name='upload'),
            path('cmfadmin/upload-file/', self.admin_view(UploadFileView.as_view()), name='upload_file'),  # File upload URL, used by AJAX
        ]

        return custom_urls + super().get_urls()

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
        self._wrapped = CMFAdminSite()


# Instantiate the custom admin site with a unique name for URL reversing and namespace distinction
site = DefaultCmfAdminSite()
