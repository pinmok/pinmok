#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
models module

Description:
  Models for CMF Backend Administration
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import ConfigCategory, ConfigType


class Menu(models.Model):
    """
    Backend admin menu item supporting multi-level hierarchy and permission control.
    """
    menu_key = models.CharField(max_length=32, unique=True, db_index=True, help_text=_("Temp uuid"), )
    title = models.CharField(max_length=50, verbose_name=_("Title"), help_text=_("Menu title displayed in the admin."))
    url = models.CharField(max_length=200, blank=True, default='', verbose_name=_("URL"),
                           help_text=_("URL or named route for the menu item."))
    icon = models.CharField(max_length=50, blank=True, default='', verbose_name=_("Icon"), help_text=_("Icon class for the menu item."))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               verbose_name=_("Parent Menu"), help_text=_("Parent menu for hierarchical structure."))
    app_label = models.CharField(max_length=50, blank=True, default='', )
    sort_order = models.PositiveIntegerField(default=10000, verbose_name=_("Sort Order"), help_text=_("Order for menu sorting."))
    permission = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Permission Code"),
                                  help_text=_("Permission code to control menu visibility."))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"), help_text=_("Whether this menu is active and visible."))
    visible = models.BooleanField(default=True, verbose_name=_("Visible"), help_text=_("Whether this menu is visible."))
    remark = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Remark"),
                              help_text=_("Additional notes or comments about this menu item."))
    update_at = models.DateTimeField(auto_now=True, verbose_name=_("Update At"),
                                     help_text=_("Time when this menu item was last updated."))

    class Meta:
        ordering = ['sort_order']
        verbose_name = _("Admin Menu")
        verbose_name_plural = _("Admin Menus")

    def __str__(self):
        return self.title


class Config(models.Model):
    """
    Config item storing key-value pairs by category with a defined type.
    Uniquely identified by (category, key).
    """
    category = models.CharField(max_length=20, choices=ConfigCategory.choices, verbose_name=_("Category"))
    key = models.CharField(max_length=64, verbose_name=_("Key"))
    value = models.TextField(verbose_name=_("Value"))
    type = models.CharField(max_length=20, choices=ConfigType.choices, default=ConfigType.TEXT, verbose_name=_("Type"))
    remark = models.CharField(max_length=255, blank=True, verbose_name=_("Remark"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Update At"))

    class Meta:
        unique_together = ('category', 'key')
        verbose_name = _('Configuration Item')
        verbose_name_plural = _('Configuration Items')

    def __str__(self):
        return f"[{self.category}] {self.key}: {self.value}"
