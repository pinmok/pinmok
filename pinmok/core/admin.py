#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin.py module

Description:
  This module re-exports `site` from pinmok.core.sites to mirror the
  usage pattern of django.contrib.admin, allowing users to replace
  `from django.contrib import admin` with `from pinmok.core import admin`
  without changing any other code.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/5/17
"""

from pinmok.core.sites import site  # noqa: F401
