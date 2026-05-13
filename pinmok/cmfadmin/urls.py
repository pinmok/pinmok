#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmfadmin.urls

Description:
  URL routing configuration for backend applications.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/1/7
"""
from django.urls import path

from pinmok.cmfadmin.views import (
    SpriteManagerView, UploadFileView, TestEmailView, ThemeView, ThemeConfigView, nav_parent_choices,
    license_page, sync_menu,
)

admin_urlpatterns = [
    path('icons/', SpriteManagerView.as_view(), name='icons_manage'),
    path('test-email/', TestEmailView.as_view(), name='test_email'),
    path('upload-file/', UploadFileView.as_view(), name='upload_file'),  # File upload URL, used by AJAX
    path('theme/', ThemeView.theme_list, name='theme_list'),
    path('theme/<str:directory>/install/', ThemeView.install, name='theme_install'),
    path('theme/<int:theme_id>/uninstall/', ThemeView.uninstall, name='theme_uninstall'),
    path('theme/<int:theme_id>/activate/', ThemeView.activate, name='theme_activate'),
    path('theme/<int:theme_id>/reset/', ThemeView.reset, name='theme_reset'),
    path('theme/<int:theme_id>/config/', ThemeConfigView.as_view(), name='theme_config'),
    path('nav/parent-choices/', nav_parent_choices, name='nav_parent_choices'),
    path('license/', license_page, name='license_page'),
    path('sync-menu/', sync_menu, name='sync_menu'),
]
