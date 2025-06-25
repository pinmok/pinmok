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


def int_to_bytes(num: int) -> str:
    """
    Convert a size in bytes to a human-readable string with an appropriate unit.

    The function converts the input byte size to the largest possible unit
    (B, KB, MB, GB, TB, PB, EB) where the value is less than 1000,
    formatting the number with two decimal places.

    Args:
        num (int or float): Size in bytes.

    Returns:
        str: Human-readable string with size and unit, e.g., "1.46 KB", "500.00 B".
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    size = float(num)
    for unit in units:
        if size < 1024:
            # Format with two decimal places first
            s = f"{size:.2f}"

            # Remove trailing zeros and decimal point if not needed,
            # e.g., '500.00' -> '500', '30.10' -> '30.1'
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return f'{s} {unit}'
        size /= 1024
    return f'{size:.2f} ZB'


def bytes_to_int(size_str: str) -> int:
    """
    Convert a human-readable size string to an integer number of bytes.

    The function parses a string representing a size with unit suffix
    (e.g., "1KB", "5 M", "2GB") and converts it to bytes.
    Supports units: B, K, KB, M, MB, G, GB, T, TB, P, PB (case-insensitive).
    If no unit is given, the input is treated as bytes.

    Args:
        size_str (str): Size string with optional unit suffix.

    Returns:
        int: Size in bytes.

    Raises:
        ValueError: If the string cannot be parsed into a number.
    """
    size_str = size_str.strip().upper()
    unit_multipliers = {
        'K': 1024, 'KB': 1024,
        'M': 1024 ** 2, 'MB': 1024 ** 2,
        'G': 1024 ** 3, 'GB': 1024 ** 3,
        'T': 1024 ** 4, 'TB': 1024 ** 4,
        'P': 1024 ** 5, 'PB': 1024 ** 5,
        'E': 1024 ** 6, 'EB': 1024 ** 6,
        'Z': 1024 ** 7, 'ZB': 1024 ** 7,
    }
    for unit in unit_multipliers:
        # Check if the size string ends with the current unit (e.g., 'KB', 'M')
        if size_str.endswith(unit):
            # Extract the numeric part by removing the unit and any surrounding whitespace
            number = float(size_str.replace(unit, '').strip())
            # Convert the number to bytes by multiplying with the unit's multiplier
            return int(number * unit_multipliers[unit])
    return int(size_str)
