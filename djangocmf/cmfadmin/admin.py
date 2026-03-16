#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin module

Description:
  Admin class definitions for DjangoCMF models.

  This module defines ModelAdmin classes and registers CMF models
  using the @cmfadmin.register() decorator.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from djangocmf import cmfadmin
from djangocmf.cmfadmin.enums import ConfigCategory, UploadConfigKey
from djangocmf.cmfadmin.forms.config_forms import EmailConfigForm, UploadConfigForm
from djangocmf.cmfadmin.forms.forms import CMFAdminPasswordResetForm, CMFAdminUserCreationForm
from djangocmf.cmfadmin.models import ExternalLink, Nav, SiteConfig, EmailConfig, UploadConfig
from djangocmf.cmfadmin.options import CMFModelAdmin, CMFModelAdminMixin, ConfigModelAdmin, ExtraPanel


@cmfadmin.register(User)
class CmfUserAdmin(CMFModelAdminMixin, UserAdmin):
    """
    Custom admin for Django's User model with CMF enhancements.
    """
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": (("first_name", "last_name"), "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    ("is_active", "is_staff", "is_superuser"),
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": (("last_login", "date_joined"),)}),
    )
    readonly_fields = ("last_login", "date_joined")
    add_form = CMFAdminUserCreationForm
    change_password_form = CMFAdminPasswordResetForm


@cmfadmin.register(Group)
class CmfGroupAdmin(CMFModelAdminMixin, GroupAdmin):
    """
    Custom admin for Django's Group model with CMF enhancements.
    """
    pass


@cmfadmin.register(SiteConfig)
class SiteConfigAdmin(ConfigModelAdmin):
    menu_order = 1000
    category = ConfigCategory.SITE
    fieldsets = [
        (_("Site Information"), {
            "fields": [
                ("site_name", "site_slogan"),
                ("site_logo", "icp", "pns"),
            ]
        }),
        (_("Contact Information"), {
            "fields": [
                ("service_phone", "service_email"),
                "contact_address",
                ("wechat_qrcode", "wechat_mini_program", "wechat_official_account"),
            ]
        }),
        (_("Social Media"), {
            "fields": [
                ("facebook_link", "x_link"),
                ("linkedin_link", "instagram_link")
            ],
            'classes': ('collapse',),
        }),
        (_("SEO Settings"), {
            "fields": [
                ("seo_title", "seo_keywords"),
                "seo_description",
            ],
            'classes': ('collapse',),
        }),
    ]


@cmfadmin.register(EmailConfig)
class EmailConfigAdmin(ConfigModelAdmin):
    menu_order = 2000
    category = ConfigCategory.EMAIL
    form = EmailConfigForm
    extra_panels = [ExtraPanel(label=_("Test Email Sending"), template="config/test_email.html", icon='tabler-mail-check')]
    fieldsets = [
        (_("Base Settings"), {
            "fields": [
                "default_from_email",
                ("smtp_host", "smtp_port", "smtp_username", "smtp_password"),
                ("smtp_use_ssl", "smtp_use_tls", "timeout")
            ]
        }),
        (_("Email Template"), {
            "fields": [
                "template_from_name",
                "template_subject",
                "template_content",
                "template_variables"
            ], 'classes': ('collapse',),
        }),
    ]


@cmfadmin.register(UploadConfig)
class UploadConfigAdmin(ConfigModelAdmin):
    menu_order = 3000
    category = ConfigCategory.UPLOAD
    form = UploadConfigForm
    fieldsets = [
        (None, {"fields": [
            (UploadConfigKey.UPLOAD_MAX_FILES, UploadConfigKey.UPLOAD_PATH_RULE),
            (UploadConfigKey.IMAGE_SIZE, UploadConfigKey.IMAGE_TYPE),
            (UploadConfigKey.AUDIO_SIZE, UploadConfigKey.AUDIO_TYPE),
            (UploadConfigKey.VIDEO_SIZE, UploadConfigKey.VIDEO_TYPE),
            (UploadConfigKey.ARCHIVE_SIZE, UploadConfigKey.ARCHIVE_TYPE),
            (UploadConfigKey.DOCUMENT_SIZE, UploadConfigKey.DOCUMENT_TYPE),
        ]})
    ]


@cmfadmin.register(ExternalLink)
class ExternalLinksAdmin(CMFModelAdmin):
    """Admin for external links management."""
    list_display = ('sort_order', 'image_thumb', 'title', 'url_link', 'status')
    list_display_links = ('title',)
    list_editable = ('sort_order',)

    def url_link(self, obj):
        """Display the URL as a link that opens in a new tab in the list view"""
        if obj.url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)
        return "-"

    url_link.short_description = 'url'
    url_link.admin_order_field = 'url'

    def image_thumb(self, obj):
        """Display thumbnail image in list view."""
        if obj.image:
            return format_html('<img src="{}" class="icon">', obj.image.url)
        return "-"

    image_thumb.short_description = _('Icon')
    image_thumb.admin_order_field = 'image_url'


@cmfadmin.register(Nav)
class NavAdmin(CMFModelAdmin):
    """Admin for navigation menu management."""
    list_display = ('title', 'slug', 'is_active', 'created_at', 'edit_nav')

    def edit_nav(self, obj):
        """Display edit menu action link."""
        url = reverse('admin:cmfadmin:nav_items_edit', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, _('Edit Menu'))

    edit_nav.short_description = _('Action')
