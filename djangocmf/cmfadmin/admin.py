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
from djangocmf.cmfadmin.fields import IndentedModelChoiceField
from djangocmf.cmfadmin.forms.config_forms import EmailConfigForm, UploadConfigForm
from djangocmf.cmfadmin.forms.forms import CMFAdminPasswordResetForm, CMFAdminUserCreationForm
from djangocmf.cmfadmin.models import ExternalLink, Nav, SiteConfig, EmailConfig, UploadConfig, NavItem
from djangocmf.cmfadmin.options import CMFModelAdmin, CMFModelAdminMixin, ConfigModelAdmin, ExtraPanel
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.widgets import CMFSelect


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
    fieldsets = [
        (None, {'fields': [
            ('title', 'url', 'sort_order'),
            ('image', 'status'),
        ]})
    ]

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


@cmfadmin.register(Nav)
class NavAdmin(CMFModelAdmin):
    """Admin for navigation menu management."""
    list_display = ('title', 'slug', 'is_active', 'created_at', 'edit_items')
    list_display_links = ('title', 'slug')

    def edit_items(self, obj):
        url = reverse('admin:cmfadmin_navitem_changelist') + f'?nav__id__exact={obj.pk}'
        return format_html('<a href="{}">{}</a>', url, _('Edit Nav Items'))

    edit_items.short_description = _('Items')


@cmfadmin.register(NavItem)
class NavItemAdmin(CMFModelAdmin):
    """Admin for navigation item management."""
    list_display = ('sort_order', 'name', 'nav', 'parent', 'url', 'is_visible')
    list_display_links = ('name',)
    list_filter = ('nav',)
    list_editable = ('sort_order', 'is_visible')
    exclude = ('nav',)
    fieldsets = [
        (None, {'fields': [
            ('name', 'url'),
            ('parent',),
            ('icon', 'target'),
            ('sort_order', 'is_visible'),
        ]})
    ]

    def get_model_perms(self, request):
        """Hide from app_list but keep accessible via direct URL."""
        return {}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'parent':
            nav_id = self._get_nav_id(request)
            kwargs['empty_label'] = _('Top Level')
            kwargs['queryset'] = NavItem.objects.filter(nav_id=nav_id) if nav_id else NavItem.objects.none()
            if nav_id:
                items = NavService.get_items(nav_id)
                # Use IndentedModelChoiceField to control option order and display.
                # queryset is kept for FK validation; choices drives the actual
                # display and DFS order from flatten_with_indent.
                return IndentedModelChoiceField(
                    pairs=items,
                    widget=CMFSelect(),
                    label=NavItem._meta.get_field('parent').verbose_name,
                    required=False,
                    **kwargs,
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Remove related widget action buttons and set parent choices with tree indentation."""
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name in ('nav', 'parent') and formfield:
            if hasattr(formfield.widget, 'can_add_related'):
                formfield.widget.can_add_related = False
                formfield.widget.can_change_related = False
                formfield.widget.can_delete_related = False
                formfield.widget.can_view_related = False
        return formfield

    def _get_nav_id(self, request):
        """Extract nav_id from request in all contexts."""
        filters = request.GET.get('_changelist_filters', '')

        if filters:
            for part in filters.split('&'):
                if part.startswith('nav__id__exact='):
                    return part.split('=')[1]

        # From existing object URL (/navitem/123/change/)
        if hasattr(request, 'resolver_match'):
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    return NavItem.objects.values_list('nav_id', flat=True).get(pk=obj_id)
                except NavItem.DoesNotExist:
                    pass
        return None

    def save_model(self, request, obj, form, change):
        if not change:
            nav_id = self._get_nav_id(request)
            if nav_id:
                obj.nav_id = nav_id
        super().save_model(request, obj, form, change)

    @property
    def back_url(self):
        return reverse('admin:cmfadmin_navitem_changelist')
