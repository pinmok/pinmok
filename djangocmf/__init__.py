#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
__init__ module

Description:
  A framework-level modular backend system providing core services, administration features,
  and extensible components for building scalable and maintainable web applications.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-05-30
"""
from django.utils.version import get_version

name = 'DjangoCMF'

VERSION = (0, 1, 0, 'alpha', 0)

__version__ = get_version(VERSION)
version = __version__
