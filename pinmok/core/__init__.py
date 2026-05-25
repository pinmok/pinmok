# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
__init__ module

Description:
  Core utilities and foundational components shared across the project.
  Provides common helpers, base classes, and global services used by other modules.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""
from django import get_version

from pinmok.core.menu import menu

VERSION = (1, 0, 0, 'alpha', 1)
__version__ = get_version(VERSION)
__author__ = "惠达浪"
__author_email = "crazys@126.com"
__title__ = "Pinmok"
__license__ = "MIT"
__description__ = "A modular backend framework for Django."
