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
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin.enums import ConfigCategory, TargetChoices
from djangocmf.core.constants import DEFAULT_SORT_ORDER


# ---------------------------------------------------------------------------
# Main menu model
# ---------------------------------------------------------------------------

class Menu(models.Model):
    """
    Backend admin menu item supporting multi-level hierarchy and permission control.
    """
    menu_key = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        db_comment="Stable hash used to uniquely identify this menu item, based on URL and parent id."
    )
    title = models.CharField(
        max_length=50,
        verbose_name=_("title"),
        db_comment="Menu title displayed in the admin."
    )
    url = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("url"),
        db_comment="URL or named route for the menu item."
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("icon"),
        db_comment="Icon class for the menu item."
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("parent menu"),
        db_comment="Parent menu for hierarchical structure."
    )
    app_label = models.CharField(
        max_length=50,
        blank=True,
        default='',
        db_comment="Application label associated with this menu item."
    )
    permissions = models.JSONField(
        max_length=255,
        blank=True,
        default=list,
        db_comment="Permissions associated with this menu item."
    )
    sort_order = models.PositiveIntegerField(
        default=DEFAULT_SORT_ORDER,
        verbose_name=_("sort order"),
        db_comment="Order for menu sorting."
    )
    remark = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("remark"),
        db_comment="Additional notes or comments about this menu item."
    )

    class Meta:
        ordering = ['sort_order']
        verbose_name = _("admin menu")
        verbose_name_plural = _("admin menus")

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Config — the single key-value table
# ---------------------------------------------------------------------------
class ConfigManager(models.Manager):
    """
    A custom manager scoped to a specific configuration category.

    Overrides get_queryset() to automatically filter by the given category,
    ensuring all queries through this manager only return records of that category.
    """

    def __init__(self, category):
        super().__init__()
        self._category = category

    def get_queryset(self):
        return super().get_queryset().filter(category=self._category)


class Config(models.Model):
    """
    Configuration item storing key-value pairs by category.
    Uniquely identified by (category, key).
    Only keys that differ from their schema defaults are stored.
    """

    category = models.CharField(
        max_length=32,
        choices=ConfigCategory,  # noqa
        verbose_name=_("category"),
        db_comment="Configuration category."
    )
    key = models.CharField(
        max_length=64,
        verbose_name=_("key"),
        db_comment="Unique configuration key.",
    )
    value = models.TextField(
        verbose_name=_("value"),
        db_comment="Configuration value.",
    )
    remark = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("remark"),
        db_comment="Additional notes about this configuration item.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        category = getattr(cls, 'category', None)
        if category is not None:
            cls.objects = ConfigManager(category)
            cls.objects.auto_created = True

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "key"], name="unique_config_category_key"),
        ]
        verbose_name = _("configuration item")
        verbose_name_plural = _("configuration items")
        # Raw Config table itself needs no custom permissions;
        # permissions are managed per-category via proxy models below.
        default_permissions = ()

    def __str__(self):
        return f"[{self.category}] {self.key}: {self.value}"


# ---------------------------------------------------------------------------
# Proxy Models — one per category
#
# Purpose:
#   1. Independent permission management via Django's native Permission system
#   2. Scoped Manager so queries are automatically filtered by category
#   3. Can add category-specific methods or properties if needed
#
# Permissions:
#   view   — controls menu visibility (checked by CMF menu filter)
#   change — controls whether the config page is editable or read-only
#
# Note: add/delete are intentionally excluded because config keys are
# defined in code (CONFIG_SCHEMA), not created/deleted by admin users.
# ---------------------------------------------------------------------------


class SiteConfig(Config):
    category = ConfigCategory.SITE

    class Meta:
        proxy = True
        default_permissions = ("view", "change")
        verbose_name = _(ConfigCategory.SITE.label)
        verbose_name_plural = _(ConfigCategory.SITE.label)


class EmailConfig(Config):
    category = ConfigCategory.EMAIL

    class Meta:
        proxy = True
        default_permissions = ("view", "change")
        verbose_name = _(ConfigCategory.EMAIL.label)
        verbose_name_plural = _(ConfigCategory.EMAIL.label)


class UploadConfig(Config):
    category = ConfigCategory.UPLOAD

    class Meta:
        proxy = True
        default_permissions = ("view", "change")
        verbose_name = _(ConfigCategory.UPLOAD.label)
        verbose_name_plural = _(ConfigCategory.UPLOAD.label)


# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------

class ExternalLink(models.Model):
    """
    Model representing a friendly external link.
    """
    title = models.CharField(
        max_length=50,
        verbose_name=_("title"),
        help_text=_("The title for the external link.")
    )
    url = models.URLField(
        verbose_name=_("url"),
        blank=True,
        help_text=_("The URL for the external link.")
    )
    image = models.ImageField(
        upload_to='links/',
        blank=True,
        null=True,
        verbose_name=_("image"),
        help_text=_("The image associated with the external link.")
    )
    status = models.BooleanField(
        default=True,
        verbose_name=_("status"),
        help_text=_("Indicates whether this link is active.")
    )
    sort_order = models.PositiveIntegerField(
        default=DEFAULT_SORT_ORDER,
        verbose_name=_("sort order"),
        help_text=_("Determines the display order of the link.")
    )

    class Meta:
        ordering = ['sort_order']
        verbose_name = _(ConfigCategory.LINKS.label)
        verbose_name_plural = _(ConfigCategory.LINKS.label)

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Navigation models
# ---------------------------------------------------------------------------

class Nav(models.Model):
    """
    Navigation container table.
    Example: Top Navigation, Footer Navigation, Main Navigation.
    """
    title = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("title"), help_text=_("The title for the navigation.")
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("slug"),
        help_text=_("A short unique identifier used in URLs and templates. Only letters, numbers, hyphens, and underscores are allowed."))
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("is active"),
        help_text=_("Whether this navigation is active.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
        help_text=_("Time when this navigation was created.")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
        help_text=_("Time when this navigation was last updated.")
    )

    class Meta:
        verbose_name = _("navigation")
        verbose_name_plural = _("navigations")
        ordering = ['id']

    def __str__(self):
        return self.title


class NavItem(models.Model):
    """
    Navigation menu item table.
    Supports multi-level nesting, sorting, icons, visibility toggles, and target options.
    """
    nav = models.ForeignKey(
        Nav,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_("navigation"),
        help_text=_("Navigation container.")
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("parent item"),
        help_text=_("Parent item for hierarchical structure.")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("name"),
        help_text=_("Name of the navigation item.")
    )
    url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("url"),
        help_text=_("URL for this navigation item.")
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("icon class"),
        help_text=_("Icon class for this navigation item.")
    )
    target = models.CharField(
        max_length=10,
        choices=TargetChoices,  # noqa
        default=TargetChoices.SELF,
        verbose_name=_("target"),
        help_text=_("Target behavior when opening the link.")
    )
    sort_order = models.PositiveIntegerField(
        default=DEFAULT_SORT_ORDER,
        verbose_name=_("sort order"),
        help_text=_("Order for navigation item sorting.")
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("is visible"),
        help_text=_("Whether this item is visible.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
        help_text=_("Time when this navigation item was created.")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
        help_text=_("Time when this navigation item was last updated.")
    )

    class Meta:
        verbose_name = _("navigation item")
        verbose_name_plural = _("navigation items")
        ordering = ['sort_order']

    def __str__(self):
        return self.name
