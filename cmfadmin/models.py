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

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from cmfadmin.constants import DEFAULT_SORT_ORDER
from cmfadmin.enums import ConfigCategory, TargetChoices, MimeType
from cmfadmin.libs.upload import UploadResult

User = get_user_model()


class Menu(models.Model):
    """
    Backend admin menu item supporting multi-level hierarchy and permission control.
    """
    menu_key = models.CharField(max_length=32, unique=True, db_index=True,
                                help_text=_("Temporary UUID used to identify this menu item."))
    title = models.CharField(max_length=50, verbose_name=_("Title"),
                             help_text=_("Menu title displayed in the admin."))
    url = models.CharField(max_length=200, blank=True, default='', verbose_name=_("URL"),
                           help_text=_("URL or named route for the menu item."))
    icon = models.CharField(max_length=50, blank=True, default='', verbose_name=_("Icon"),
                            help_text=_("Icon class for the menu item."))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               verbose_name=_("Parent Menu"),
                               help_text=_("Parent menu for hierarchical structure."))
    app_label = models.CharField(max_length=50, blank=True, default='',
                                 help_text=_("Application label associated with this menu item."))
    sort_order = models.PositiveIntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_("Sort Order"),
                                             help_text=_("Order for menu sorting."))
    permission = models.JSONField(blank=True, default=list, verbose_name=_("Permission Code"),
                                  help_text=_("List of permission codes required to view this menu item."))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"),
                                    help_text=_("Whether this menu is active and visible."))
    visible = models.BooleanField(default=True, verbose_name=_("Visible"),
                                  help_text=_("Whether this menu is visible."))
    remark = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Remark"),
                              help_text=_("Additional notes or comments about this menu item."))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"),
                                      help_text=_("Time when this menu item was last updated."))

    class Meta:
        ordering = ['sort_order']
        verbose_name = _("Admin Menu")
        verbose_name_plural = _("Admin Menus")

    def __str__(self):
        return self.title


class Config(models.Model):
    """
    Configuration item storing key-value pairs by category with a defined type.
    Uniquely identified by (category, key).
    """
    category = models.CharField(max_length=20, choices=ConfigCategory.choices,
                                verbose_name=_("Category"), help_text=_("Configuration category."))
    key = models.CharField(max_length=64, verbose_name=_("Key"), help_text=_("Unique configuration key."))
    value = models.TextField(verbose_name=_("Value"), help_text=_("Configuration value."))
    remark = models.CharField(max_length=255, blank=True, verbose_name=_("Remark"),
                              help_text=_("Additional notes about this configuration item."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"),
                                      help_text=_("Time when this configuration was created."))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"),
                                      help_text=_("Time when this configuration was last updated."))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['category', 'key'], name='unique_config_category_key'),
        ]
        verbose_name = _('Configuration Item')
        verbose_name_plural = _('Configuration Items')

    def __str__(self):
        return f"[{self.category}] {self.key}: {self.value}"


class ExternalLink(models.Model):
    """
    Model representing a friendly external link.
    """
    title = models.CharField(max_length=50, verbose_name=_("Title"),
                             help_text=_("The title for the external link."))
    url = models.URLField(verbose_name=_("URL"), blank=True,
                          help_text=_("The URL for the external link."))
    image_url = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Image"),
                                 help_text=_("The image associated with the external link."))
    status = models.BooleanField(default=True, verbose_name=_("Status"),
                                 help_text=_("Indicates whether this link is active."))
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
    Navigation container table.
    Example: Top Navigation, Footer Navigation, Main Navigation.
    """
    title = models.CharField(max_length=100, unique=True, verbose_name=_("Title"),
                             help_text=_("The title for the navigation."))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug"),
                            help_text=_("A short unique identifier used in URLs and templates. "
                                        "Only letters, numbers, hyphens, and underscores are allowed."))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"),
                                    help_text=_("Whether this navigation is active."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"),
                                      help_text=_("Time when this navigation was created."))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"),
                                      help_text=_("Time when this navigation was last updated."))

    class Meta:
        verbose_name = _("Navigation")
        verbose_name_plural = _("Navigations")
        ordering = ['id']

    def __str__(self):
        return self.title


class NavItem(models.Model):
    """
    Navigation menu item table.
    Supports multi-level nesting, sorting, icons, visibility toggles, and target options.
    """
    nav = models.ForeignKey(Nav, on_delete=models.CASCADE, related_name='items',
                            verbose_name=_("Navigation"), help_text=_("Navigation container."))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               verbose_name=_("Parent Item"), help_text=_("Parent item for hierarchical structure."))
    name = models.CharField(max_length=100, verbose_name=_("Name"),
                            help_text=_("Name of the navigation item."))
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("URL"),
                           help_text=_("URL for this navigation item."))
    icon = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Icon Class"),
                            help_text=_("Icon class for this navigation item."))
    target = models.CharField(max_length=10, choices=TargetChoices.choices, default=TargetChoices.SELF,
                              verbose_name=_("Target"), help_text=_("Target behavior when opening the link."))
    sort_order = models.IntegerField(default=DEFAULT_SORT_ORDER, verbose_name=_("Sort Order"),
                                     help_text=_("Order for navigation item sorting."))
    is_visible = models.BooleanField(default=True, verbose_name=_("Is Visible"),
                                     help_text=_("Whether this item is visible."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"),
                                      help_text=_("Time when this navigation item was created."))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"),
                                      help_text=_("Time when this navigation item was last updated."))

    class Meta:
        verbose_name = _("Navigation Item")
        verbose_name_plural = _("Navigation Items")
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class UploadFile(models.Model):
    """
    Model to store metadata for each uploaded file.
    """
    uploader = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_files',
                                 verbose_name=_("Uploader"), help_text=_("The user who uploaded the file (optional)."))
    filename = models.CharField(max_length=255, verbose_name=_("Filename"),
                                help_text=_("Saved file name including extension."))
    original_name = models.CharField(max_length=255, verbose_name=_("Original Name"),
                                     help_text=_("Original file name before upload."))
    path = models.CharField(max_length=500, verbose_name=_("Path"),
                            help_text=_("Relative path to the saved file."))
    mime_type = models.CharField(max_length=100, choices=MimeType.choices, verbose_name=_("MIME Type"),
                                 help_text=_("MIME type of the uploaded file."))
    size = models.BigIntegerField(verbose_name=_("Size"),
                                  help_text=_("File size in bytes."))
    hash = models.CharField(max_length=64, db_index=True, unique=True, verbose_name=_("Hash"),
                            help_text=_("SHA-256 hash of the file content."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"),
                                      help_text=_("Upload timestamp."))

    class Meta:
        verbose_name = _('Uploaded File')
        verbose_name_plural = _('Uploaded Files')

    def __str__(self):
        return self.original_name

    @classmethod
    def create_from_result(cls, result: UploadResult, user: User = None):
        obj, created = cls.objects.get_or_create(
            hash=result.hash,
            defaults={
                'uploader': user,
                'filename': result.filename,
                'original_name': result.original_name,
                'path': result.path,
                'mime_type': result.mime_type,
                'size': result.size,
            }
        )
        return obj

    def to_result(self) -> UploadResult:
        return UploadResult(
            path=self.path,
            filename=self.filename,
            size=self.size,
            mime_type=self.mime_type,
            original_name=self.original_name,
            hash=self.hash,
        )
