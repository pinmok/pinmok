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
    SiteInfoView,
    EmailConfigView,
    SpriteManagerView,
    nav_items_edit,
    NavItemView,
    FileManagementView,
    UploadSettingView,
    UploadFileView
)

admin_urlpatterns = [
    path('site/', SiteInfoView.as_view(), name='site_config'),
    path('email/', EmailConfigView.as_view(), name='email_config'),
    path('icons/', SpriteManagerView.as_view(), name='icons_manage'),
    path('nav/<int:pk>/', nav_items_edit, name='nav_items_edit'),
    path('nav/navitem/<int:nav_id>/<int:nav_item_id>/', NavItemView.as_view(), name='navitem'),
    path('files/', FileManagementView.as_view(), name='file_management'),
    path('upload/', UploadSettingView.as_view(), name='upload'),
    path('upload-file/', UploadFileView.as_view(), name='upload_file'),  # File upload URL, used by AJAX
]
