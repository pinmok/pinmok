#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorization module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-09-09
"""

from django.core.cache import cache

from cmfadmin.models import Menu

CACHE_KEY = "permission_service_menu_map_v1"
CACHE_TTL = 30  # 秒，可根据负载调整


class PermissionService:
    """
    Unified permission checking for menus and custom paths.
    Rules:
      - superuser -> always allow
      - path matches menu.url prefix -> check menu.permission
      - path matches custom registered prefix -> check corresponding permission
      - longest prefix match wins
      - if no matching rule -> allow
    """
    custom_rules = []

    @classmethod
    def _normalize_prefix(cls, path: str) -> str:
        """Normalize path to standard form for prefix matching"""
        if not path:
            return ""
        if not path.startswith("/"):
            path = "/" + path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path

    @classmethod
    def _load_menu_map(cls):
        """
        Load menu URL → permission mapping from DB, cache it to reduce DB hits.
        Returns list of {"url": normalized_url, "perm": permission_code}
        """
        menu_map = cache.get(CACHE_KEY)
        if menu_map is not None:
            return menu_map

        menu_map = []
        qs = Menu.objects.exclude(url__exact="").exclude(permission__exact="")
        for m in qs:
            perms = m.permission or []
            if isinstance(perms, str):
                perms = [perms]
            menu_map.append({
                "url": cls._normalize_prefix(m.url),
                "perm": perms
            })

        cache.set(CACHE_KEY, menu_map, CACHE_TTL)
        return menu_map

    @classmethod
    def check(cls, user, path: str) -> bool:
        """
        Return True if user is allowed to access 'path'.
        """
        if getattr(user, "is_superuser", False):
            return True

        path_norm = cls._normalize_prefix(path)
        candidates = []

        # menu rules
        for item in cls._load_menu_map():
            if path_norm.startswith(item["url"]):
                candidates.append(item)

        # custom rules
        for rule in cls.custom_rules:
            prefix = cls._normalize_prefix(rule["prefix"])
            if path_norm.startswith(prefix):
                candidates.append({"url": prefix, "perm": rule["permission"]})

        if not candidates:
            # no matching rule -> allow by default
            return True

        # choose the most specific match (longest prefix)
        chosen = max(candidates, key=lambda x: len(x["url"]))
        perm = chosen.get("perm")
        if perm is None:
            return True
        if isinstance(perm, str):
            return user.has_perm(perm)
        if isinstance(perm, list):
            return any(user.has_perm(p) for p in perm)
        raise ValueError(_("Invalid permission type: %(type)s") % {"type": type(perm)})

    @classmethod
    def register(cls, path_prefix: str, permission: str):
        """
        Register custom API/plugin path → permission mapping.
        permission: "app_label.codename"
        """
        cls.custom_rules.append({
            "prefix": path_prefix,
            "permission": permission
        })

    @classmethod
    def clear_cache(cls):
        cache.delete(CACHE_KEY)
