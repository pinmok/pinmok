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

from djangocmf.cmfadmin.views import SpriteManagerView, UploadFileView, TestEmailView

admin_urlpatterns = [
    path('icons/', SpriteManagerView.as_view(), name='icons_manage'),
    path('test-email/', TestEmailView.as_view(), name='test_email'),
    path('upload-file/', UploadFileView.as_view(), name='upload_file'),  # File upload URL, used by AJAX
]
