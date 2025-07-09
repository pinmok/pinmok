#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urls module

Description:
  CMF Admin urls
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""

from cmfadmin.views import (
    sync_menu,
    SiteInfoView,
    EmailConfigView,
    nav_items_edit,
    NavItemView,
    SpriteManagerView,
)

cmfadmin_urls = [
    ('sync_menu', sync_menu, 'sync_menu'),
    ('cmfadmin/site/', SiteInfoView.as_view(), 'site_config'),
    ('cmfadmin/email/', EmailConfigView.as_view(), 'email_config'),
    ('cmfadmin/icons/', SpriteManagerView.as_view(), 'icons_manage'),
    ('cmfadmin/nav/<int:pk>/', nav_items_edit, 'nav_items_edit'),
    ('cmfadmin/nav/navitem/<int:nav_id>/<int:nav_item_id>/', NavItemView.as_view(), 'navitem'),
]
