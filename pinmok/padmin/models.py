#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
models module

Description:
  Models for Pinmok Backend Administration
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import resolve, Resolver404
from django.utils.translation import gettext_lazy as _

from pinmok.core.constants import DEFAULT_SORT_ORDER, TRANSLATION_RELATED_NAME
from pinmok.core.translatable import TranslatableModel, TranslationModel
from pinmok.padmin.enums import ConfigCategory, TargetChoices, FileType

User = get_user_model()


class Menu(models.Model):
    """
    Backend admin menu item supporting multi-level hierarchy and permission control.
    """
    menu_key = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Stable hash used to uniquely identify this menu item, based on URL and parent id."
    )
    title = models.CharField(
        max_length=50,
        verbose_name=_("title"),
        help_text="Menu title displayed in the admin."
    )
    url = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("url"),
        help_text="URL or named route for the menu item."
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("icon"),
        help_text="Icon class for the menu item."
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("parent menu"),
        help_text="Parent menu for hierarchical structure."
    )
    app_label = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Application label associated with this menu item."
    )
    permissions = models.JSONField(
        max_length=255,
        blank=True,
        default=list,
        help_text="Permissions associated with this menu item."
    )
    sort_order = models.PositiveIntegerField(
        default=DEFAULT_SORT_ORDER,
        verbose_name=_("sort order"),
        help_text="Order for menu sorting."
    )
    remark = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("remark"),
        help_text="Additional notes or comments about this menu item."
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
        help_text="Configuration category."
    )
    key = models.CharField(
        max_length=64,
        verbose_name=_("key"),
        help_text="Unique configuration key.",
    )
    value = models.TextField(
        verbose_name=_("value"),
        help_text="Configuration value.",
    )
    remark = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("remark"),
        help_text="Additional notes about this configuration item.",
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
#   view   — controls menu visibility (checked by Pinmok menu filter)
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
        verbose_name = _("Site Information")
        verbose_name_plural = _("Site Information")


class EmailConfig(Config):
    category = ConfigCategory.EMAIL

    class Meta:
        proxy = True
        default_permissions = ("view", "change")
        verbose_name = _("Email Setting")
        verbose_name_plural = _("Email Settings")


class UploadConfig(Config):
    category = ConfigCategory.UPLOAD

    class Meta:
        proxy = True
        default_permissions = ("view", "change")
        verbose_name = _("Upload Setting")
        verbose_name_plural = _("Upload Settings")


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
        verbose_name = _('Partner Link')
        verbose_name_plural = _('Partner Links')

    def __str__(self):
        return self.title


class Resource(models.Model):
    """
    Represents an uploaded file or external media resource.

    Local files are stored as relative paths (e.g. '2026/03/abc123.jpg').
    External resources store the full URL directly.
    Deduplication: local files by SHA-256 hash, external resources by url.
    """
    url = models.CharField(
        'URL',
        max_length=2048,
        unique=True,
        help_text=_('Relative path for local files, full URL for external resources.')
    )
    original_name = models.CharField(
        _('original name'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('The original file name of the uploaded file')
    )
    size = models.PositiveIntegerField(
        _('size'),
        default=0,
        help_text=_('File size in bytes. 0 for external resources.')
    )
    hash = models.CharField(
        _('hash'),
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        help_text=_('SHA-256 hex digest. Empty for external resources.')
    )
    file_type = models.CharField(
        _('file type'),
        max_length=20,
        choices=FileType.choices,  # noqa
        blank=True,
        default='',
    )
    mime_type = models.CharField(
        _('MIME type'),
        max_length=100,
        blank=True,
        default='',
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources',
        verbose_name=_('uploaded by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('resource')
        verbose_name_plural = _('resources')
        ordering = ['-created_at']

    def __str__(self):
        return self.original_name or self.url


class Nav(TranslatableModel):
    """
    Navigation item. Language-neutral structure.
    Use group to distinguish which navigation group this item belongs to.
    """
    group = models.CharField(
        max_length=100,
        verbose_name=_("group"),
        help_text=_("Which navigation group this item belongs to.")
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
    url = models.CharField(
        max_length=255,
        blank=True,
        default='',
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
        choices=TargetChoices,
        default=TargetChoices.SELF,
        verbose_name=_("target"),
        help_text=_("Target behavior when opening the link.")
    )
    sort_order = models.PositiveIntegerField(
        default=DEFAULT_SORT_ORDER,
        verbose_name=_("sort order"),
        help_text=_("Order for sorting.")
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("is visible"),
        help_text=_("Whether this item is visible.")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("navigation")
        verbose_name_plural = _("navigations")
        ordering = ['group', 'sort_order']


class NavTranslation(TranslationModel):
    """
    Language-specific translation for a navigation item.
    """
    nav = models.ForeignKey(
        Nav,
        on_delete=models.CASCADE,
        related_name=TRANSLATION_RELATED_NAME,
        verbose_name=_("navigation item"),
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("Display name of this navigation item.")
    )

    class Meta:
        verbose_name = _("nav translation")
        verbose_name_plural = _("nav translations")
        unique_together = [('nav', 'language')]

    def get_display_text(self):
        return self.name


class UrlAlias(models.Model):
    alias = models.CharField(
        _('Alias'),
        max_length=255,
        unique=True,
        help_text=_('The alias path without leading slash, e.g. news or about/team'),
    )
    target = models.CharField(
        _('Target URL'),
        max_length=255,
        help_text=_(
            'The internal URL path this alias points to, must start with a leading slash and must be a valid registered URL,'
            ' e.g. /content/category/abc123/'
        ),
    )
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validate that target resolves to a known view
        try:
            resolve(self.target)
        except Resolver404:
            raise ValidationError({'target': _('Target URL does not resolve to a known view.')})

    class Meta:
        verbose_name = _('URL Alias')
        verbose_name_plural = _('URL Aliases')

    def __str__(self):
        return f'{self.alias} → {self.target}'


class Theme(models.Model):
    """Installed theme, corresponds to theme.json"""
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    author = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    preview = models.CharField(max_length=200, blank=True)
    directory = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=False)
    installed_at = models.DateTimeField(auto_now_add=True)
    config = models.JSONField(default=dict)

    class Meta:
        verbose_name = _('theme')
        verbose_name_plural = _('themes')
        ordering = ['-installed_at']

    def __str__(self):
        return f'{self.name} {self.version}'


class ThemeTemplate(models.Model):
    """Page template within a theme, corresponds to each page JSON"""
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='templates')
    filename = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=DEFAULT_SORT_ORDER)
    config = models.JSONField(default=dict)

    class Meta:
        verbose_name = _('theme template')
        verbose_name_plural = _('theme templates')
        ordering = ['sort_order']
        unique_together = ('theme', 'filename')

    def __str__(self):
        return f'{self.theme.name} / {self.name}'


class Slider(models.Model):
    title = models.CharField(max_length=200, blank=True, verbose_name=_('title'))
    subtitle = models.TextField(blank=True, verbose_name=_('subtitle'))
    image = models.ImageField(upload_to='slider/', blank=True, verbose_name=_('image'))
    link = models.CharField(max_length=200, blank=True, verbose_name=_('link'))
    group = models.CharField(max_length=100, verbose_name=_('group'))
    sort_order = models.IntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_('order'))
    is_active = models.BooleanField(default=True, verbose_name=_('status'))

    class Meta:
        verbose_name = _('slider')
        verbose_name_plural = _('sliders')
        ordering = ['group', 'sort_order']

    def __str__(self):
        return f'[{self.group}] {self.title}'
