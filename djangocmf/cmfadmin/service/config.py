#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config service

Description:
  Three-layer architecture for reading and writing CMF configuration:

  ConfigCache   — Django cache wrapper; supports per-key and per-category caching.
  ConfigStore   — Database read/write layer; operates on the Config table as raw
                  strings, with no type conversion.
  ConfigService — Public API; combines schema lookup, type conversion, cache,
                  and store. This is the only layer callers should use directly.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""

import json
import logging
from datetime import datetime
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.utils.dateparse import parse_datetime

from djangocmf.cmfadmin.config_schema import CONFIG_SCHEMA
from djangocmf.cmfadmin.constants import CMF_CONFIG_CACHE_TTL
from djangocmf.cmfadmin.enums import ConfigType
from djangocmf.cmfadmin.models import Config

logger = logging.getLogger(__name__)


class ConfigCache:
    """
    Thin wrapper around Django's cache framework.

    Two granularities are supported:
      - Per-key   : a single (category, key) value, stored as a raw string.
      - Per-category : all rows of a category, stored as {key: raw_str} dict.

    The caller is responsible for deciding which granularity to invalidate.
    """

    _KEY_PREFIX = "cmf_cfg"
    _CAT_PREFIX = "cmf_cfg_cat"

    # --- key helpers --------------------------------------------------------

    @staticmethod
    def _key(category: str, key: str) -> str:
        return f"{ConfigCache._KEY_PREFIX}:{category}:{key}"

    @staticmethod
    def _cat_key(category: str) -> str:
        return f"{ConfigCache._CAT_PREFIX}:{category}"

    # --- per-key operations -------------------------------------------------

    def get(self, category: str, key: str) -> str | None:
        """Return the cached raw string, or None if not cached."""
        return cache.get(self._key(category, key))

    def set(self, category: str, key: str, raw_value: str) -> None:
        cache.set(self._key(category, key), raw_value, timeout=CMF_CONFIG_CACHE_TTL)

    def delete(self, category: str, key: str) -> None:
        cache.delete(self._key(category, key))

    # --- per-category operations --------------------------------------------

    def get_category(self, category: str) -> dict[str, str] | None:
        """Return a {key: raw_str} dict for the whole category, or None if not cached."""
        return cache.get(self._cat_key(category))

    def set_category(self, category: str, data: dict[str, str]) -> None:
        cache.set(self._cat_key(category), data, timeout=CMF_CONFIG_CACHE_TTL)

    def delete_category(self, category: str) -> None:
        cache.delete(self._cat_key(category))

    def invalidate(self, category: str, key: str) -> None:
        """Invalidate both the per-key entry and the whole category cache."""
        self.delete(category, key)
        self.delete_category(category)


class ConfigStore:
    """
    Raw database access layer.  No type conversion is done here.
    All values going in and coming out are plain strings.
    """

    @staticmethod
    def get(category: str, key: str) -> str | None:
        """
        Return the stored string value, or None if the row does not exist.
        """
        try:
            obj = Config.objects.get(category=category, key=key)
            return obj.value
        except Config.DoesNotExist:
            return None

    @staticmethod
    def get_category(category: str) -> dict[str, str]:
        """
        Return all rows for a category as {key: raw_str}.
        """
        qs = Config.objects.filter(category=category).values("key", "value")
        return {row["key"]: row["value"] for row in qs}

    @staticmethod
    def set(category: str, key: str, raw_value: str) -> None:
        """
        Upsert a single key.  Creates the row if it does not exist.
        """
        Config.objects.update_or_create(
            category=category,
            key=key,
            defaults={"value": raw_value},
        )

    @staticmethod
    def set_many(category: str, data: dict[str, str]) -> None:
        """
        Upsert multiple keys for the same category in a single transaction.
        """
        with transaction.atomic():
            for key, raw_value in data.items():
                ConfigStore.set(category, key, raw_value)

    @staticmethod
    def delete(category: str, key: str) -> None:
        Config.objects.filter(category=category, key=key).delete()


# ===========================================================================
# Type conversion helpers
# ===========================================================================

def _serialize(cfg_type: ConfigType, value: Any) -> str:
    """
    Convert a Python value to the raw string stored in the DB.
    Raises ValueError if the value cannot be serialized for the given type.
    """
    if value is None:
        return ""

    match cfg_type:
        case ConfigType.BOOL:
            # Accept both bool and string "true"/"false" for convenience.
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, str) and value.lower() in ("true", "false"):
                return value.lower()
            raise ValueError(f"Cannot serialize {value!r} as BOOL")

        case ConfigType.INT | ConfigType.FLOAT:
            return str(value)

        case ConfigType.JSON:
            if isinstance(value, str):
                # Validate it is valid JSON before storing.
                json.loads(value)
                return value
            return json.dumps(value, ensure_ascii=False)

        case ConfigType.DATETIME:
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)

        case ConfigType.MULTI_SELECT:
            if isinstance(value, (list, tuple)):
                return ",".join(str(v) for v in value)
            # Already a comma-separated string.
            return str(value)

        case _:
            # STR, TEXT, EMAIL, URL, IP, IMAGE, FILE — store as-is.
            return str(value)


def _deserialize(cfg_type: ConfigType, raw: str) -> Any:
    """
    Convert a raw DB string to the appropriate Python type.
    Returns the raw string on conversion failure (logs a warning).
    """
    match cfg_type:
        case ConfigType.BOOL:
            return raw.lower() == "true"

        case ConfigType.INT:
            if raw == "":
                return None
            try:
                return int(raw)
            except (ValueError, TypeError):
                logger.warning("ConfigService: cannot convert %r to int", raw)
                return None

        case ConfigType.FLOAT:
            if raw == "":
                return None
            try:
                return float(raw)
            except (ValueError, TypeError):
                logger.warning("ConfigService: cannot convert %r to float", raw)
                return None

        case ConfigType.JSON:
            if raw == "":
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("ConfigService: cannot parse JSON %r", raw)
                return raw

        case ConfigType.DATETIME:
            if raw == "":
                return None
            dt = parse_datetime(raw)
            if dt is None:
                logger.warning("ConfigService: cannot parse datetime %r", raw)
            return dt

        case ConfigType.MULTI_SELECT:
            if raw == "":
                return []
            return [v for v in raw.split(",") if v]

        case _:
            # STR, TEXT, EMAIL, URL, IP, IMAGE, FILE — return as-is.
            return raw


class ConfigService:
    """
    Public API for reading and writing CMF configuration.

    All callers should use this class.  ConfigCache and ConfigStore are
    implementation details and should not be called directly outside this
    module.

    Usage examples::

        # Read a single value (typed)
        name = ConfigService.get(ConfigCategory.SITE, "site_name")

        # Read all values for a category (typed dict)
        site = ConfigService.get_category(ConfigCategory.SITE)

        # Write a single value
        ConfigService.set(ConfigCategory.SITE, "site_name", "My Site")

        # Write multiple values at once (e.g. from a form save)
        ConfigService.set_many(ConfigCategory.EMAIL, {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
        })
    """

    _cache = ConfigCache()

    # -----------------------------------------------------------------------
    # Schema helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _schema_for(category: str) -> dict:
        """Return the schema dict for a category, or {} if not defined."""
        return CONFIG_SCHEMA.get(category, {})

    @staticmethod
    def _field_schema(category: str, key: str) -> dict:
        """Return the schema entry for a single key, or {} if not found."""
        return ConfigService._schema_for(category).get(key, {})

    @staticmethod
    def _default(category: str, key: str) -> str:
        """
        Return the schema default as a raw string.
        For MULTI_SELECT the default is already a comma-separated string.
        For BOOL the default must be True/False (converted here to "true"/"false").
        """
        schema = ConfigService._field_schema(category, key)
        default = schema.get("default", "")
        cfg_type = schema.get("type", ConfigType.STR)

        if cfg_type == ConfigType.BOOL and isinstance(default, bool):
            return "true" if default else "false"
        if default is None:
            return ""
        return str(default)

    # -----------------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------------

    @classmethod
    def get(cls, category: str, key: str) -> Any:
        """
        Return the typed value for a single key.

        Lookup order: per-key cache → DB → schema default.
        The result is cached before returning.
        """
        cached = cls._cache.get(category, key)
        if cached is not None:
            schema = cls._field_schema(category, key)
            cfg_type = schema.get("type", ConfigType.STR)
            return _deserialize(cfg_type, cached)

        raw = ConfigStore.get(category, key)
        if raw is None:
            raw = cls._default(category, key)

        cls._cache.set(category, key, raw)

        schema = cls._field_schema(category, key)
        cfg_type = schema.get("type", ConfigType.STR)
        return _deserialize(cfg_type, raw)

    @classmethod
    def get_category(cls, category: str) -> dict[str, Any]:
        """
        Return all config values for a category as a typed dict.

        Keys present in the schema but absent from the DB are filled with
        their schema defaults.  Keys in the DB but absent from the schema
        are included as raw strings (no conversion).

        Lookup order: category cache → DB → merge with defaults.
        """
        cached = cls._cache.get_category(category)
        if cached is not None:
            return cls._apply_schema(category, cached)

        db_rows = ConfigStore.get_category(category)
        cls._cache.set_category(category, db_rows)
        return cls._apply_schema(category, db_rows)

    @classmethod
    def _apply_schema(cls, category: str, db_rows: dict[str, str]) -> dict[str, Any]:
        """
        Merge DB rows with schema defaults and apply type conversion.
        Returns a {key: typed_value} dict covering every key in the schema.
        """
        schema = cls._schema_for(category)
        result: dict[str, Any] = {}

        # Keys defined in the schema.
        for key, field in schema.items():
            cfg_type = field.get("type", ConfigType.STR)
            if key in db_rows:
                raw = db_rows[key]
            else:
                raw = cls._default(category, key)
            result[key] = _deserialize(cfg_type, raw)

        # Keys in DB but not in schema — include as raw strings.
        for key, raw in db_rows.items():
            if key not in result:
                result[key] = raw

        return result

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    @classmethod
    def set(cls, category: str, key: str, value: Any) -> None:
        """
        Persist a single typed value.

        The value is serialized according to the schema type before storage.
        Both the per-key cache and the category cache are invalidated.
        """
        schema = cls._field_schema(category, key)
        cfg_type = schema.get("type", ConfigType.STR)
        raw = _serialize(cfg_type, value)

        ConfigStore.set(category, key, raw)
        cls._cache.invalidate(category, key)

    @classmethod
    def set_many(cls, category: str, data: dict[str, Any]) -> None:
        """
        Persist multiple typed values for a category in one DB transaction.

        Each value is serialized individually according to its schema type.
        All related cache entries (per-key and category) are invalidated.
        """
        schema = cls._schema_for(category)
        raw_data: dict[str, str] = {}

        for key, value in data.items():
            cfg_type = schema.get(key, {}).get("type", ConfigType.STR)
            raw_data[key] = _serialize(cfg_type, value)

        ConfigStore.set_many(category, raw_data)

        # Invalidate per-key caches and the category cache.
        for key in data:
            cls._cache.delete(category, key)
        cls._cache.delete_category(category)

    # -----------------------------------------------------------------------
    # Utility
    # -----------------------------------------------------------------------

    @classmethod
    def get_raw(cls, category: str, key: str) -> str:
        """
        Return the raw stored string without type conversion.
        Useful for pre-populating form fields that display the stored value.
        """
        cached = cls._cache.get(category, key)
        if cached is not None:
            return cached
        raw = ConfigStore.get(category, key)
        if raw is None:
            raw = cls._default(category, key)
        cls._cache.set(category, key, raw)
        return raw

    @classmethod
    def get_category_raw(cls, category: str) -> dict[str, str]:
        """
        Return all raw string values for a category (no type conversion),
        merging DB rows with schema defaults for missing keys.
        """
        cached = cls._cache.get_category(category)
        if cached is not None:
            db_rows = cached
        else:
            db_rows = ConfigStore.get_category(category)
            cls._cache.set_category(category, db_rows)

        schema = cls._schema_for(category)
        result: dict[str, str] = {}

        for key, field in schema.items():
            if key in db_rows:
                result[key] = db_rows[key]
            else:
                result[key] = cls._default(category, key)

        # Include extra DB keys not in schema.
        for key, raw in db_rows.items():
            if key not in result:
                result[key] = raw

        return result

    @classmethod
    def invalidate(cls, category: str, key: str | None = None) -> None:
        """
        Manually invalidate cache entries.
        If key is None, invalidates the entire category cache.
        If key is given, invalidates both the per-key and category caches.
        """
        if key is not None:
            cls._cache.invalidate(category, key)
        else:
            cls._cache.delete_category(category)
