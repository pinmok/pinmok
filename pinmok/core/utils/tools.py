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


def int_to_bytes(num: int) -> str:
    """
    Convert a size in bytes to a human-readable string with an appropriate unit.

    Args:
        num (int): Size in bytes. Must be non-negative.

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


def to_snake_case(text: str) -> str:
    """
    Convert text into a snake_case string safe for identifiers (permissions, menu codes, etc.).

    Rules:
    - Strip leading/trailing spaces
    - Keep letters, digits, underscores, and CJK characters
    - Replace other characters (punctuation, symbols, etc.) with underscores
    - Collapse multiple underscores into one
    - Remove leading/trailing underscores
    - Convert to lowercase

    Example:
        "Site Info"        -> "site_info"
        "User@List(Admin)" -> "user_list_admin"
        "---Config---"     -> "config"
    """
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


def to_compact_case(text: str) -> str:
    """
    Convert a string into a compact, lowercase form by removing all spaces
    and non-alphanumeric/non-CJK characters. Letters, digits, and CJK characters
    are preserved. Output is in lowercase.

    Examples:
        "Site Setting" -> "sitesetting"
        "User List(Admin)" -> "userlistadmin"
    """
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]", "", str(text), flags=re.UNICODE)
    return cleaned.lower()


def to_camel_case(text: str) -> str:
    """
    Convert a string into camelCase by removing spaces and symbols, preserving letters, digits, and CJK characters.
    The first word is lowercase, subsequent words have their first letter capitalized.

    Examples:
        "Site Setting"        -> "siteSetting"
        "User List(Admin)"    -> "userListAdmin"
    """

    # Split by non-alphanumeric/non-CJK characters
    parts = re.split(r"[^\w\u4e00-\u9fff]+", text, flags=re.UNICODE)
    # Remove empty parts
    parts = [p for p in parts if p]
    if not parts:
        return ""

    # First part lowercase, rest capitalize first letter
    first = parts[0].lower()
    rest = [p[0].upper() + p[1:] if len(p) > 1 else p.upper() for p in parts[1:]]
    return first + "".join(rest)
