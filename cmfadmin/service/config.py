#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config module

Description:
  CMF Config Service
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-24
"""
from typing import Any

from django.core.cache import cache

from cmfadmin.enums import ConfigCategory
from cmfadmin.models import Config


class ConfigService:
    CACHE_PREFIX = 'crazy_cmf_config'
    CATEGORY_PREFIX = CACHE_PREFIX + '_category'

    @classmethod
    def _cache_key(cls, key: str) -> str:
        """Generate the cache key for a specific config key."""
        return f'{cls.CACHE_PREFIX}:{key}'

    @classmethod
    def _category_cache_key(cls, category: str) -> str:
        """Generate the cache key for a config category."""
        return f'{cls.CATEGORY_PREFIX}:{category}'

    @classmethod
    def get(cls, key: str | list | tuple, default: Any = None) -> Any | dict:
        keys = [key] if isinstance(key, str) else list(key)
        result = {}

        for k in keys:
            cache_key = cls._cache_key(k)
            val = cache.get(cache_key)
            if val is None:
                try:
                    obj = Config.objects.get(key=k)
                    val = obj.value
                    cache.set(cache_key, val)
                except Config.DoesNotExist:
                    val = default
            result[k] = val

        return result[key] if isinstance(key, str) else result

    @classmethod
    def set(cls, category: ConfigCategory, key: str, value: Any):
        obj, _ = Config.objects.update_or_create(
            key=key,
            defaults={'value': value, 'category': category}
        )

        # Update key cache
        cache.set(cls._cache_key(key), value)

        # Update category cache
        category_key = cls._category_cache_key(category)
        category_data = cache.get(category_key) or {}
        category_data[key] = value
        cache.set(category_key, category_data)

    @classmethod
    def get_by_category(cls, category: ConfigCategory) -> dict:
        cache_key = cls._category_cache_key(category)
        if (data := cache.get(cache_key)) is not None:
            return data

        # Retrieve all configuration items for the given category with a single database query
        data = {
            item.key: item.value
            for item in Config.objects.filter(category=category).only('key', 'value')
        }
        cache.set(cache_key, data)

        # Set cache for keys in batch
        cache.set_many({cls._cache_key(k): v for k, v in data.items()})

        return data

    @classmethod
    def set_by_category(cls, category: ConfigCategory, data: dict[str, Any]):
        """
        Batch set config items under the given category.
        """
        category_data = {}

        for key, value in data.items():
            Config.objects.update_or_create(
                category=category,
                key=key,
                defaults={'value': value}
            )
            cache.set(cls._cache_key(key), value)
            category_data[key] = value

        cache.set(cls._category_cache_key(category), category_data)

    @staticmethod
    def delete(key: str | list | tuple | None = None, category: ConfigCategory | None = None) -> int:
        """
        Delete config(s) by key(s) and/or category, and clear corresponding cache.

        Returns:
            int: Number of deleted records
        """
        if key is None and category is None:
            return 0

        deleted_count = 0

        if key is not None:
            keys = [key] if isinstance(key, str) else list(key)

            for k in keys:
                qs = Config.objects.filter(key=k)
                if category is not None:
                    qs = qs.filter(category=category)

                count, _ = qs.delete()
                deleted_count += count

                # Clear cache for this key
                cache.delete(ConfigService._cache_key(k))

        if category is not None:
            # Delete all configs in this category
            qs = Config.objects.filter(category=category)
            deleted_items = qs.only("key")
            deleted_keys = [item.key for item in deleted_items]

            count, _ = qs.delete()
            deleted_count += count

            # Clear key-level caches
            cache.delete_many([ConfigService._cache_key(k) for k in deleted_keys])

            # Clear category-level cache if category is given
            cache.delete(ConfigService._category_cache_key(category))

        return deleted_count
