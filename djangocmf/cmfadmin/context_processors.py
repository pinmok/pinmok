#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_processors module

Description:
  Global context processor for CMF frontend.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/4/24
"""
from django.core.cache import cache

from djangocmf.cmfadmin.constants import CMF_CONFIG_CACHE_TTL, EXTERNAL_LINK_CACHE_KEY
from djangocmf.cmfadmin.enums import ConfigCategory
from djangocmf.cmfadmin.models import ExternalLink
from djangocmf.cmfadmin.service.config import ConfigService


def _get_external_links():
    """
    Return all active external links from cache or database.
    Results are cached to avoid repeated queries on every request.
    """
    links = cache.get(EXTERNAL_LINK_CACHE_KEY)
    if links is None:
        links = list(ExternalLink.objects.filter(status=True).order_by('sort_order').values('title', 'url', 'image'))
        cache.set(EXTERNAL_LINK_CACHE_KEY, links, CMF_CONFIG_CACHE_TTL)
    return links


def site(request):
    """
    Inject global site configuration into every template context.
    Only active on frontend pages; admin pages use CMFAdminSite.each_context().
    """
    return {
        "site_info": ConfigService.get_category(ConfigCategory.SITE),
        "external_links": _get_external_links(),
    }
