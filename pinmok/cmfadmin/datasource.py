#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
datasource module

Description:
  Provides a centralized registry for mapping datasource identifiers to Django Widget classes.
  It supports both decorator-based and direct registration, enabling flexible extension of
  datasource-driven form rendering.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/4/13
"""
from django.forms.widgets import Widget
from django.utils.translation import gettext_lazy as _

from pinmok.cmfadmin.models import Slider, Nav
from pinmok.cmfadmin.widgets import CMFSelect


class DataSourceRegistry:
    """Registry mapping source keys to Widget classes for datasource variables."""

    def __init__(self):
        self._registry: dict[str, type[Widget]] = {}

    def register(self, key: str, widget_class: type[Widget] = None):
        """
        Register a Widget class under the given key.
        Can be used as a decorator or called directly.
        """

        def _do_register(cls):
            if not issubclass(cls, Widget):
                raise TypeError(
                    f"{cls.__name__} must subclass forms.Widget"
                )
            self._registry[key] = cls
            return cls

        if widget_class is not None:
            return _do_register(widget_class)
        return _do_register

    def get(self, key: str) -> type[Widget] | None:
        return self._registry.get(key)

    def all_keys(self) -> list[str]:
        return list(self._registry.keys())

    def is_registered(self, key: str) -> bool:
        return key in self._registry


datasource = DataSourceRegistry()


@datasource.register('nav')
class NavDataSource(CMFSelect):
    def __init__(self, attrs=None):
        groups = Nav.objects.filter(is_visible=True).values_list('group', flat=True).distinct()
        choices = [('', _('None'))] + [(n, n) for n in groups]
        super().__init__(attrs=attrs, choices=choices)


@datasource.register('slider')
class SliderDataSource(CMFSelect):
    def __init__(self, attrs=None):
        groups = Slider.objects.filter(is_active=True).values_list('group', flat=True).distinct()
        choices = [('', _('None'))] + [(g, g) for g in groups]
        super().__init__(attrs=attrs, choices=choices)
