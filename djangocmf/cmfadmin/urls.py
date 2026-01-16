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

from djangocmf.cmfadmin.views import (
    license_page,
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

admin_urlpatterns = [
    path('license/', license_page, name='license_page'),
    path('sync-menu/', sync_menu, name='sync_menu'),
    path('profile/', UserProfile.as_view(), name='profile'),
    path('cmf/site/', SiteInfoView.as_view(), name='site_config'),
    path('cmf/email/', EmailConfigView.as_view(), name='email_config'),
    path('cmf/icons/', SpriteManagerView.as_view(), name='icons_manage'),
    path('cmf/nav/<int:pk>/', nav_items_edit, name='nav_items_edit'),
    path('cmf/nav/navitem/<int:nav_id>/<int:nav_item_id>/', NavItemView.as_view(), name='navitem'),
    path('cmf/files/', FileManagementView.as_view(), name='file_management'),
    path('cmf/upload/', UploadSettingView.as_view(), name='upload'),
    path('cmf/upload-file/', UploadFileView.as_view(), name='upload_file'),  # File upload URL, used by AJAX
]
