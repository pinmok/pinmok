#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config module

Description:
    A lightweight, high-performance configuration management service with cache-layer abstraction
    and atomic database operations.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-24
"""
from typing import Any, Iterable

from django.core.cache import cache
from django.db import transaction
from django.db.utils import OperationalError

from djangocmf.cmfadmin.enums import ConfigCategory
from djangocmf.cmfadmin.models import Config


class ConfigCache:
    """
    Lightweight cache helper class.
    Responsible only for cache I/O, no business logic.
    """

    PREFIX = "crazy_cmf_config"
    TIMEOUT = 3600
    NULL = object()  # Sentinel for caching missing keys

    # --- Key Generators ---

    @classmethod
    def key(cls, k: str) -> str:
        """Return full cache key for a single config key."""
        return f"{cls.PREFIX}:{k}"

    @classmethod
    def category_key(cls, c: str) -> str:
        """Return full cache key for a config category."""
        return f"{cls.PREFIX}:cat:{c}"

    # --- Basic Cache Operations ---

    @classmethod
    def get_many(cls, keys: Iterable[str]) -> dict[str, Any]:
        """Batch get config values from cache."""
        cache_keys = {k: cls.key(k) for k in keys}
        cached = cache.get_many(cache_keys.values())
        result = {}
        for k, ck in cache_keys.items():
            if ck in cached:
                val = cached[ck]
                result[k] = None if val is cls.NULL else val
        return result

    @classmethod
    def set_many(cls, data: dict[str, Any]) -> None:
        """Batch set config values into cache."""
        if not data:
            return
        mapped = {cls.key(k): (v if v is not None else cls.NULL) for k, v in data.items()}
        cache.set_many(mapped, cls.TIMEOUT)

    @classmethod
    def delete_many(cls, keys: Iterable[str]) -> None:
        """Batch delete config cache keys."""
        cache.delete_many([cls.key(k) for k in keys])

    # --- Category Cache Operations ---

    @classmethod
    def get_category(cls, category: str) -> dict[str, Any] | None:
        """Get entire category data from cache."""
        return cache.get(cls.category_key(category))

    @classmethod
    def set_category(cls, category: str, data: dict[str, Any]) -> None:
        """Cache all config items under one category."""
        cache.set(cls.category_key(category), data, cls.TIMEOUT)

    @classmethod
    def delete_category(cls, category: str) -> None:
        """Delete cached category data."""
        cache.delete(cls.category_key(category))


class ConfigStore:
    """
    Database helper class.
    Contains only ORM logic, no caching or business logic.
    """

    @staticmethod
    def fetch(keys: Iterable[str]) -> dict[str, Any]:
        """Fetch config values by key list."""
        return {c.key: c.value for c in Config.objects.filter(key__in=keys).only("key", "value")}

    @staticmethod
    def fetch_by_category(category: ConfigCategory) -> dict[str, Any]:
        """Fetch all configs under a given category."""
        return {c.key: c.value for c in Config.objects.filter(category=category).only("key", "value")}

    @staticmethod
    def save(category: ConfigCategory, key: str, value: Any) -> None:
        """Insert or update a single config record."""
        Config.objects.update_or_create(key=key, defaults={"value": value, "category": category})

    @staticmethod
    def save_many(category: ConfigCategory, data: dict[str, Any]) -> None:
        """Batch insert or update configs atomically."""
        with transaction.atomic():
            for k, v in data.items():
                Config.objects.update_or_create(category=category, key=k, defaults={"value": v})

    @staticmethod
    def delete(keys: list[str]) -> int:
        """Delete configs by key list."""
        return Config.objects.filter(key__in=keys).delete()[0]

    @staticmethod
    def delete_by_category(category: ConfigCategory) -> int:
        """Delete all configs under a category."""
        return Config.objects.filter(category=category).delete()[0]


class ConfigService:
    """
    Unified configuration service.
    Combines cache layer and DB layer to minimize queries while ensuring consistency.
    """

    # --- Read Operations ---

    @classmethod
    def get(cls, keys: str | list[str] | tuple[str, ...], default: Any = None) -> Any | dict[str, Any]:
        """
        Get single or multiple config values with transparent caching.
        Args:
            keys: Single key or list/tuple of keys
            default: Default value for missing keys
        Returns:
            Single value or dict of values
        """
        single = isinstance(keys, str)
        keys = [keys] if single else list(keys)

        try:
            # Read from cache
            cached = ConfigCache.get_many(keys)

            # If cache is None or empty, fallback to empty dict
            if not isinstance(cached, dict):
                cached = {}

            # Determine which keys are missing or invalid
            missing = [k for k in keys if k not in cached or cached[k] is None]

            # Query DB for missing keys
            if missing:
                db_data = ConfigStore.fetch(missing)
                ConfigCache.set_many(db_data)

                # Cache NULL for truly missing keys
                missed = {k: default for k in missing if k not in db_data}
                ConfigCache.set_many(missed)

                cached.update(db_data)
                cached.update(missed)
        except OperationalError:
            # DB down fallback
            cached = {k: default for k in keys}

        # Ensure defaults (also cover cached None values)
        for k in keys:
            if cached.get(k) is None:
                cached[k] = default

        return cached[keys[0]] if single else cached

    @classmethod
    def get_by_category(cls, category: ConfigCategory) -> dict[str, Any]:
        """
        Get all config items under a category.
        Uses category-level cache first, then falls back to DB.
        """
        cached = ConfigCache.get_category(category)
        if cached is not None:
            return cached

        try:
            data = ConfigStore.fetch_by_category(category)
            ConfigCache.set_category(category, data)
            ConfigCache.set_many(data)
            return data
        except OperationalError:
            return {}

    # --- Write Operations ---

    @classmethod
    def set(cls, category: ConfigCategory, key: str, value: Any) -> None:
        """
        Update a single config item.
        Ensures cache consistency between key and category.
        """
        try:
            ConfigStore.save(category, key, value)
            ConfigCache.set_many({key: value})

            # Update category cache in-place if available
            cat_data = ConfigCache.get_category(category)
            if cat_data is not None:
                cat_data[key] = value
                ConfigCache.set_category(category, cat_data)
        except OperationalError:
            pass

    @classmethod
    def set_by_category(cls, category: ConfigCategory, data: dict[str, Any]) -> None:
        """
        Batch update multiple configs under a category.
        All operations are atomic.
        """
        if not data:
            return
        try:
            ConfigStore.save_many(category, data)
            ConfigCache.set_many(data)
            ConfigCache.set_category(category, data)
        except OperationalError:
            pass

    # --- Delete Operations ---

    @classmethod
    def delete(
            cls,
            keys: str | list[str] | tuple[str, ...] | None = None,
            category: ConfigCategory | None = None
    ) -> int:
        """
        Delete configs by key or category.
        Ensures both DB and cache consistency.
        """
        if not keys and not category:
            return 0

        try:
            deleted_keys: list[str] = []
            count = 0

            # Delete by key(s)
            if keys:
                keys = [keys] if isinstance(keys, str) else list(keys)
                count += ConfigStore.delete(keys)
                deleted_keys.extend(keys)

            # Delete by category
            if category:
                deleted_keys.extend(ConfigStore.fetch_by_category(category).keys())
                count += ConfigStore.delete_by_category(category)
                ConfigCache.delete_category(category)

            # Cache cleanup
            if deleted_keys:
                ConfigCache.delete_many(deleted_keys)

            return count
        except OperationalError:
            return 0
