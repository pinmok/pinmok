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
import logging
import os
import platform
import shutil

from django import get_version
from django.apps import apps
from django.conf import settings
from django.db import connection, utils

import djangocmf
from djangocmf.core.utils.tools import int_to_bytes

logger = logging.getLogger(__name__)


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
        'cmf_name': djangocmf.core.__title__,
        'cmf_version': djangocmf.core.__version__,
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
    total, used, free = shutil.disk_usage(settings.BASE_DIR)
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
        tuple[str, str]: A tuple of (vendor, version).
        vendor is the capitalized database vendor name (e.g., 'Postgresql').
        version is the database server version string. Both default to 'Unknown' if unavailable.
    """
    vendor = 'Unknown'
    db_version = 'Unknown'

    try:
        vendor = connection.vendor

        with  connection.cursor() as cursor:
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
                    if result:
                        db_version = result[0]
                    else:
                        cursor.execute(
                            "SELECT VERSION FROM PRODUCT_COMPONENT_VERSION WHERE PRODUCT LIKE 'Oracle Database%'")
                        result = cursor.fetchone()
                        db_version = result[0] if result else 'Unknown'
                case 'microsoft':
                    cursor.execute('SELECT @@VERSION')
                    db_version = cursor.fetchone()[0]
                case _:
                    logger.warning("Unsupported database vendor: %s", vendor)
    except utils.DatabaseError as e:
        logger.error("Database error while retrieving DB info: %s", e)
    except AttributeError as e:
        logger.error("Database connection is not properly configured: %s", e)

    return vendor.capitalize(), db_version


def get_valid_app_labels(exclude_prefixes: list[str] | None = None) -> set[str]:
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
    base_path = settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static')
    return os.path.abspath(os.path.normpath(base_path))
