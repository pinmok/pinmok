#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
__init__ module

Description:

Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""

from django.utils.version import get_version

from djangocmf.core.menu import menu
from djangocmf.core.sites import site

VERSION = (0, 1, 0, 'alpha', 0)
__version__ = get_version(VERSION)

__author__ = "惠达浪"
__author_email = "crazys@126.com"
__name__ = "DjangoCMF"
__license__ = "MIT"
__description__ = "A modular backend framework for Django."
