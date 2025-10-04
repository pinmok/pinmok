#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools utility

Description:
  Utility tools for various operations
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-10
"""
import re


def int_to_bytes(num: float) -> str:
    """
    Convert a size in bytes to a human-readable string with an appropriate unit.

    Args:
        num (int or float): Size in bytes. Must be non-negative.

    Returns:
        str: Human-readable string with size and unit, e.g., "1.46 KB", "500 B".

    Raises:
        ValueError: If input is negative.
    """
    if num < 0:
        raise ValueError("Input must be non-negative")

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']
    if num == 0:
        return "0 B"

    size = float(num)
    for i, unit in enumerate(units):
        if size < 1024 or i == len(units) - 1:
            if unit == 'B':
                return f"{int(size)} {unit}"
            else:
                s = f"{size:.2f}".rstrip('0').rstrip('.')
                return f"{s} {unit}"
        size /= 1024
    return f"{size:.2f} ZB"  # fallback, should never reach here


def bytes_to_int(size_str: str) -> int:
    """
    Convert a human-readable size string to bytes. Supports flexible formats like
    "1KB", "5 M", "2Gb", "100b", etc.

    Args:
        size_str (str): Size string with optional unit.

    Returns:
        int: Size in bytes.

    Raises:
        ValueError: If input format is invalid or unit is unrecognized.
        TypeError: If input is not a string.
    """
    if not isinstance(size_str, str):
        raise TypeError("Input must be a string")

    s = size_str.strip().upper().replace(' ', '')  # remove spaces and normalize
    if not s:
        raise ValueError("Empty input string")

    # Unit mapping
    unit_multipliers = {
        'B': 1,
        'K': 1024, 'KB': 1024,
        'M': 1024 ** 2, 'MB': 1024 ** 2,
        'G': 1024 ** 3, 'GB': 1024 ** 3,
        'T': 1024 ** 4, 'TB': 1024 ** 4,
        'P': 1024 ** 5, 'PB': 1024 ** 5,
        'E': 1024 ** 6, 'EB': 1024 ** 6,
        'Z': 1024 ** 7, 'ZB': 1024 ** 7,
    }

    # Match the longest unit first to avoid partial matches
    for unit in sorted(unit_multipliers, key=len, reverse=True):
        if s.endswith(unit):
            try:
                number = float(s[:-len(unit)])
            except ValueError:
                raise ValueError(f"Invalid number in size string: '{size_str}'")
            if number < 0:
                raise ValueError("Size cannot be negative")
            return int(number * unit_multipliers[unit])

    # No unit found, treat as bytes
    try:
        number = float(s)
    except ValueError:
        raise ValueError(f"Invalid size string: '{size_str}'")
    if number < 0:
        raise ValueError("Size cannot be negative")
    return int(number)


def safe_identifier(title: str) -> str:
    """
    Convert a string into a safe identifier for code, key, or slug.
    - Strip leading/trailing spaces
    - Lowercase
    - Replace non-word characters with underscore
    """
    return re.sub(r"\W+", "_", title.strip().lower())
