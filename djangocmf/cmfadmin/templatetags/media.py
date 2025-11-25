#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
media module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-29
"""

from django import template
from django.core.files.storage import default_storage

register = template.Library()


@register.simple_tag
def media_url(path: str) -> str:
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return path
    return default_storage.url(path)
