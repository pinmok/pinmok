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
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from djangocmf import cmfadmin
from djangocmf.cmfadmin.enums import ConfigCategory, UploadConfigKey, FileType, MimeType
from djangocmf.cmfadmin.fields import IndentedModelChoiceField
from djangocmf.cmfadmin.forms.config_forms import EmailConfigForm, UploadConfigForm
from djangocmf.cmfadmin.forms.forms import CMFAdminPasswordResetForm, CMFAdminUserCreationForm
from djangocmf.cmfadmin.models import ExternalLink, Nav, SiteConfig, EmailConfig, UploadConfig, NavItem, Resource
from djangocmf.cmfadmin.options import CMFModelAdmin, CMFModelAdminMixin, ConfigModelAdmin, ExtraPanel
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.service.upload import UploadService
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
                ("smtp_username", "smtp_password"),
                ("smtp_host", "smtp_port"),
                ("timeout", "smtp_use_ssl", "smtp_use_tls")
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
    menu_order = 5000
    list_display = ('sort_order', 'image_thumb', 'title', 'url_link', 'status')
    list_display_links = ('title',)
    list_editable = ('sort_order',)
    fieldsets = [
        (None, {'fields': [
            ('title', 'url', 'sort_order'),
            ('image', 'status'),
        ]})
    ]

    @admin.display(description='URL', ordering='url')
    def url_link(self, obj):
        """Display the URL as a link that opens in a new tab in the list view"""
        if obj.url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)
        return "-"

    @admin.display(description=_('Icon'))
    def image_thumb(self, obj):
        """Display thumbnail image in list view."""
        if obj.image:
            return format_html('<img src="{}" class="icon">', obj.image.url)
        return "-"


@cmfadmin.register(Nav)
class NavAdmin(CMFModelAdmin):
    """Admin for navigation menu management."""
    menu_order = 6000
    list_display = ('title', 'slug', 'is_active', 'created_at', 'items_action')
    list_display_links = ('title', 'slug')

    @admin.display(description=_('Items'))
    def items_action(self, obj):
        url = reverse('admin:cmfadmin_navitem_changelist') + f'?nav__id__exact={obj.pk}'
        return format_html('<a href="{}">{}</a>', url, _('Edit Nav Items'))


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
            'parent',
            ('name', 'url'),
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
        """
        Defined as a property because reverse() must be called at runtime,
        not at class definition time when URLs are not yet registered.
        """
        return reverse('admin:cmfadmin_navitem_changelist')


@cmfadmin.register(Resource)
class ResourceAdmin(CMFModelAdmin):
    """
    Admin interface for the Resource model.

    Dual purpose:
    1. Standalone management interface for uploaded files and external resources.
    2. Popup selector for all ForeignKey(Resource) fields across the entire admin,
       served automatically via the raw_id widget mechanism — no per-admin
       configuration required.

    Customization guide:
    - list_display   : add/remove column names freely
    - list_filter    : add/remove filter classes or field names freely
    - search_fields  : add/remove field names freely
    - readonly_fields: controls which fields are editable on the change form
    """
    # --- Upload form template for add view ---
    add_form_template = 'admin/widgets/resource_add_form.html'

    # --- List display ---
    list_display = [
        'thumbnail_preview',
        'original_name',
        'file_type',
        'mime_type',
        'size',
        'uploaded_by',
        'created_at',
    ]
    list_display_links = ['original_name']

    # --- Filters (add/remove entries freely) ---
    list_filter = [
        'file_type',
    ]

    # --- Search (add/remove field names freely) ---
    search_fields = [
        'original_name',
        'url',
    ]

    # --- Read-only fields on change form ---
    readonly_fields = [
        'original_name',
        'thumbnail_preview',
        'url',
        'hash',
        'size',
        'mime_type',
        'file_type',
        'uploaded_by',
        'created_at',
    ]

    ordering = ['-created_at']

    @admin.display(description=_('preview'))
    def thumbnail_preview(self, obj):
        """
        Render a thumbnail for image-type resources.
        Non-image types render a dash placeholder.
        """
        if obj.file_type == FileType.IMAGE:
            if obj.url.startswith(('http://', 'https://')):
                src = obj.url
            else:
                src = default_storage.url(obj.url)
            return format_html(
                '<img src="{}" style="height:40px;width:auto;'
                'object-fit:cover;border-radius:3px;" alt="">',
                src,
            )
        return '—'

    def add_view(self, request, form_url='', extra_context=None):
        """
        Replace the standard add form with a file upload form.

        GET:  Render upload form with allowed MIME types for <input accept>.
        POST: Receive uploaded file, delegate to UploadService, then follow
              standard admin success flow (redirect to list or dismiss popup).
        """
        # Permission check — reuse admin's built-in mechanism
        if not self.has_add_permission(request):
            raise PermissionDenied

        # Build service in all-types mode (file_type=None)
        service = UploadService(file_type=None, user=request.user)

        if request.method == 'POST':
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                messages.error(request, _('No file was uploaded.'))
                return self._render_upload_form(request, service, form_url, extra_context)

            try:
                resource = service.save(uploaded_file)
            except ValidationError as e:
                messages.error(request, e.message)
                return self._render_upload_form(request, service, form_url, extra_context)
            except Exception as e:
                messages.error(request, _('Upload failed: %(error)s') % {'error': e})
                return self._render_upload_form(request, service, form_url, extra_context)

            # Popup mode — notify opener and close window
            if IS_POPUP_VAR in request.POST:
                return self.response_add(request, resource)

            # Normal mode — redirect to change list with success message
            messages.success(request, _('Resource uploaded successfully.'))
            return HttpResponseRedirect(
                reverse(
                    'admin:%s_%s_changelist' % (
                        self.model._meta.app_label,
                        self.model._meta.model_name,
                    )
                )
            )

        return self._render_upload_form(request, service, form_url, extra_context)

    def _render_upload_form(self, request, service, form_url='', extra_context=None):
        """Render the upload form with accepted MIME types in template context."""
        # Convert MIME list to comma-separated string for <input accept>
        accepted_mimes = service.get_accepted_mimes()

        context = {
            **self.admin_site.each_context(request),
            'title': _('Upload Resource'),
            'accepted_mimes': ','.join(accepted_mimes),
            'accepted_extensions': ', '.join(MimeType.to_extensions(accepted_mimes)),
            'form_url': form_url,
            'is_popup': IS_POPUP_VAR in request.GET or IS_POPUP_VAR in request.POST,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            **(extra_context or {}),
        }
        return TemplateResponse(request, self.add_form_template, context)
