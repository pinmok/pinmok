#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
console module

Description:
  Console output utility with ANSI colors.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-08
"""
import sys


class Console:
    """Lightweight color console printer for CLI feedback."""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"

    @classmethod
    def _format(cls, label: str, color: str, msg: str) -> str:
        """Return formatted message with optional color."""
        if sys.stdout.isatty():
            return f"{color}[{label}]{cls.RESET} {msg}"
        return f"[{label}] {msg}"

    @classmethod
    def info(cls, msg: str):
        print(cls._format("INFO", cls.CYAN, msg))

    @classmethod
    def warn(cls, msg: str):
        print(cls._format("WARNING", cls.YELLOW, msg))

    @classmethod
    def error(cls, msg: str):
        print(cls._format("ERROR", cls.RED, msg))

    @classmethod
    def debug(cls, msg: str):
        print(cls._format("DEBUG", cls.BLUE, msg))

    @classmethod
    def success(cls, msg: str):
        print(cls._format("DONE", cls.GREEN, msg))
