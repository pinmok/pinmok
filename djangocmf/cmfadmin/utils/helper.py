#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper utilities

Description:
  Helper functions for common tasks
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-06
"""
import os
import platform
import shutil
from typing import Type

from django import get_version
from django.apps import apps
from django.conf import settings
from django.db import connection, utils, models
from django.db.models import Model

import djangocmf
from djangocmf.core.utils.tools import int_to_bytes


def get_system_info() -> dict[str, str]:
    """
    Gather basic system information and return it as a dictionary with translated keys.

    The returned information includes:
    - Operating system platform string
    - Python version
    - Django version
    - Disk usage (total, used, free) converted to human-readable strings
    - Current working directory (project path)

    Note:
    The dictionary keys are passed through Django's translation function (`_`)
    to support internationalization.

    Returns:
        dict: A dictionary with translated keys and corresponding system info values.
    """
    db_vendor, db_version = get_db_info()

    system_info = {
        'os': platform.platform(),
        'python_version': platform.python_version(),
        'django_version': get_version(),
        'db_vendor': db_vendor,
        'db_version': db_version,
        'cmf_name': djangocmf.__title__,
        'cmf_version': djangocmf.__version__,
    }
    return system_info


def get_disk_info() -> dict[str, str | float]:
    """
    Retrieve disk usage statistics for the root directory.

    Returns:
        dict: A dictionary containing the following keys:
            - 'total' (str): Total disk space formatted as a human-readable string.
            - 'used' (str): Used disk space formatted as a human-readable string.
            - 'free' (str): Free disk space formatted as a human-readable string.
            - 'used_percent' (float): Percentage of used disk space rounded to two decimal places.
    """
    total, used, free = shutil.disk_usage("/")
    used_percent = round(used / total * 100, 2)

    disk_info = {
        'total': int_to_bytes(total),
        'used': int_to_bytes(used),
        'free': int_to_bytes(free),
        'used_percent': used_percent,
    }
    return disk_info


def get_db_info() -> tuple[str, str]:
    """
    Retrieve the current database server version as a string.

    Returns:
        tuple(vendor, db_version): The database server vendor and version, or 'Unknown' if unavailable.
    """
    vendor = 'Unknown'
    db_version = 'Unknown'

    try:
        cursor = connection.cursor()
        vendor = connection.vendor

        match vendor:
            case 'sqlite':
                cursor.execute('SELECT sqlite_version()')
                db_version = cursor.fetchone()[0]
            case 'postgresql':
                cursor.execute('SELECT version()')
                db_version = cursor.fetchone()[0]
            case 'mysql':
                cursor.execute('SELECT VERSION()')
                db_version = cursor.fetchone()[0]
            case 'oracle':
                cursor.execute("SELECT banner FROM v$version WHERE banner LIKE 'Oracle%'")
                result = cursor.fetchone()
                db_version = result[0] if result else 'Unknown'
            case _:
                pass
    except utils.DatabaseError:
        pass
    except (AttributeError, ValueError):
        pass

    return vendor.capitalize(), db_version


def get_model_fields(model: Type[Model]) -> list[str]:
    """
    Get all manually assignable field names for a Django model.

    Excludes:
    - Auto-increment fields (AutoField, BigAutoField)
    - Auto-created fields (reverse relations)
    - Auto date fields (auto_now, auto_now_add)
    - Relation fields (ForeignKey, OneToOne, ManyToMany)

    Args:
        model: The Django model class.

    Returns:
        list[str]: A list of manually assignable field names.
    """
    fields = []
    # noinspection PyProtectedMember
    for f in model._meta.get_fields():
        if not f.concrete:
            continue  # skip non-database fields (like @property)

        if f.auto_created:
            continue  # skip auto-created fields (like reverse relations)

        if getattr(f, 'auto_now', False) or getattr(f, 'auto_now_add', False):
            continue  # skip auto date fields

        if isinstance(f, (models.AutoField, models.BigAutoField)):
            continue  # skip auto-increment primary keys

        if f.is_relation:
            continue  # skip all relation fields (ForeignKey, OneToOne, ManyToMany)

        fields.append(f.name)

    return fields


def get_valid_app_labels(exclude_prefixes: str | None = None) -> set[str]:
    """
    Return a set of valid installed app labels, optionally excluding apps
    whose full names start with any prefix in exclude_prefixes.

    Args:
        exclude_prefixes (list[str] | None): List of app name prefixes to exclude.
            Defaults to ['django.'] to exclude Django system apps.

    Returns:
        set[str]: Set of valid app labels.
    """
    if exclude_prefixes is None:
        exclude_prefixes = ['django.']

    valid_labels = {
        app.label for app in apps.get_app_configs()
        if not any(app.name.startswith(prefix) for prefix in exclude_prefixes)
    }
    return valid_labels


def get_static_dir() -> str:
    """
    Get normalized static directory path with guaranteed trailing separator
    """
    base_path = (
        settings.STATIC_ROOT
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT
        else os.path.join(settings.BASE_DIR, 'static')
    )
    return os.path.abspath(os.path.join(os.path.normpath(base_path), ''))
