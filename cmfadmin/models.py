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

from cmfadmin.constants import DEFAULT_SORT_ORDER
from cmfadmin.enums import ConfigCategory, TargetChoices


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
    sort_order = models.PositiveIntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_("Sort Order"),
                                             help_text=_("Order for menu sorting."))
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
    remark = models.CharField(max_length=255, blank=True, verbose_name=_("Remark"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Update At"))

    class Meta:
        unique_together = ('category', 'key')
        verbose_name = _('Configuration Item')
        verbose_name_plural = _('Configuration Items')

    def __str__(self):
        return f"[{self.category}] {self.key}: {self.value}"


class ExternalLink(models.Model):
    """Model representing a friendly external link."""
    title = models.CharField(max_length=50, verbose_name=_("Title"), help_text=_("The title for the external link."))
    url = models.URLField(verbose_name=_("URL"), blank=True, help_text=_("The URL for the external link."))
    image = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Image"),
                             help_text=_("The image for the external link."))
    status = models.BooleanField(default=True, verbose_name=_("Status"), help_text=_("Indicates whether this link is active."))
    sort_order = models.IntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_("Sort Order"),
                                     help_text=_("Determines the display order of the link."))

    class Meta:
        ordering = ['sort_order']
        verbose_name = _('External Link')
        verbose_name_plural = _('External Links')

    def __str__(self):
        return self.title


class Nav(models.Model):
    """
    Navigation container table
    Example: Top Navigation, Footer Navigation, Main Navigation
    """
    title = models.CharField(max_length=100, unique=True, verbose_name=_("Title"), help_text=_("The title for the navigation."))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug"),
                            help_text=_(
                                "A short unique identifier for this navigation, used in URLs and templates. Only letters, numbers, hyphens, and underscores are allowed."))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Navigation")
        verbose_name_plural = _("Navigations")
        ordering = ['id']

    def __str__(self):
        return self.title


class NavItem(models.Model):
    """
    Navigation menu item table
    Supports multi-level nesting, sorting, icons, visibility toggles, and target options
    """
    nav = models.ForeignKey(Nav, on_delete=models.CASCADE, related_name='items', verbose_name=_("Navigation"))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               verbose_name=_("Parent Item"))
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="URL")
    icon = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Icon Class"))
    target = models.CharField(max_length=10, choices=TargetChoices.choices, default=TargetChoices.SELF, verbose_name=_("Target"))
    sort_order = models.IntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_("Sort Order"))
    is_visible = models.BooleanField(default=True, verbose_name=_("Is Visible"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Navigation Item")
        verbose_name_plural = _("Navigation Items")
        ordering = ['sort_order']

    def __str__(self):
        return self.name
