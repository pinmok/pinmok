#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_processor module

Description:
  The context processor of CMF
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-15
"""
from django.conf import settings

import djangocmf
from djangocmf.cmfadmin import site
from djangocmf.cmfadmin.enums import ConfigCategory
from djangocmf.cmfadmin.menus import AdminMenuManager
from djangocmf.cmfadmin.service.config import ConfigService


def cmf_context(request):
    """Unified CMF global context."""
    admin_context = {}
    if request.path.startswith('/admin/'):
        menu_tree = AdminMenuManager.get_admin_menu(request)
        breadcrumbs = AdminMenuManager.get_admin_breadcrumb(request, menu_tree)
        admin_context = {
            'admin_menu': menu_tree,
            'admin_breadcrumbs': breadcrumbs
        }
    config = ConfigService.get_by_category(ConfigCategory.SITE)

    return {
        'SOFTWARE_NAME': djangocmf.__name__,
        'site_header': site.site_header,
        'site_title': site.site_title,
        'config': config,
        'USE_I18N': settings.USE_I18N,
        **admin_context
    }
