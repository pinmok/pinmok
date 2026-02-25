#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
views module

Description:
  CMF backend views
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-05-30
"""
import json
import os
from json import JSONDecodeError

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from djangocmf.cmfadmin.constants import CUSTOM_SPRITE_FILE, UPLOAD_FILE_CONFIG
from djangocmf.cmfadmin.enums import ConfigCategory, TargetChoices, FileType, MenuSyncMode
from djangocmf.cmfadmin.forms import NavItemForm
from djangocmf.cmfadmin.menus import AdminMenuManager
from djangocmf.cmfadmin.models import Nav, NavItem
from djangocmf.cmfadmin.service.authorization import PermissionRequiredMixin, permission_required
from djangocmf.cmfadmin.service.config import ConfigService
from djangocmf.cmfadmin.service.email import EmailService
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.service.upload import UploadService
from djangocmf.cmfadmin.utils.helper import get_static_dir
from djangocmf.core import api
from djangocmf.core.api import ErrorCode
from djangocmf.core.libs.sprite import SpriteManager, SpriteError
from djangocmf.core.libs.upload import UploadPathRule
from djangocmf.core.utils.tools import to_compact_case


def license_page(request):
    """Serve the License information page."""
    return render(request, 'pages/license.html')


class BaseAdminView(PermissionRequiredMixin, View):
    """Base class for DjangoCMF admin."""
    feature_name: str | None = None
    exclude_keys: list[str] = ['csrfmiddlewaretoken']

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Generate permission_required
        if getattr(cls, "feature_name", None):
            app_label = apps.get_containing_app_config(cls.__module__).label
            safe_title = to_compact_case(cls.feature_name)
            cls.permission_required = f"view_{app_label}:{safe_title}"

    def _get_cleaned_data(self, request) -> dict[str, str | list[str]]:
        """
        Filter out excluded POST keys and trim values.
        Preserves all values for multi-value fields (returns list).
        """
        data = {}
        for key, values in request.POST.lists():
            if key in self.exclude_keys:
                continue

            # POST responses are always lists; extract the item when only one is expected.
            if len(values) == 1:
                data[key] = values[0].strip()
            else:
                data[key] = ','.join(v.strip() for v in values if v.strip())

        return data


class SiteInfoView(BaseAdminView):
    """
    Site configuration management.
    Handles site metadata and logo upload.
    """
    feature_name = ConfigCategory.SITE.label

    def get(self, request, *args, **kwargs):
        template_name = 'config/site_info.html'
        try:
            config = ConfigService.get_by_category(ConfigCategory.SITE)
            context = {'config': config, 'title': ConfigCategory.SITE.label}
            return render(request, template_name, context)
        except Exception as e:
            messages.error(request, _('Error: %(error)s') % {'error': e})
            return render(request, template_name, {'title': ConfigCategory.SITE.label})

    def post(self, request, *args, **kwargs):
        # Handle file upload
        logo_path = None
        file = request.FILES.get('site_logo')
        if file:
            try:
                upload_service = UploadService()
                upload_result = upload_service.save(file, FileType.IMAGE, request.user)
                logo_path = upload_result.path
            except Exception as e:
                messages.error(request, _("Failed to upload '%(name)s': %(error)s") % {
                    "name": file.name,
                    "error": e
                })

        # Prepare data
        data = self._get_cleaned_data(request)
        if logo_path:
            data['site_logo'] = logo_path

        # Save data
        try:
            if data:
                ConfigService.set_by_category(ConfigCategory.SITE, data)
                messages.success(request, _("Configuration updated successfully."))
            else:
                messages.warning(request, _("No valid data submitted."))
        except Exception as e:
            messages.error(request, _("Failed to save configuration: %(error)s") % {"error": e})

        return self.get(request, *args, **kwargs)


class UploadSettingView(BaseAdminView):
    """
    File upload settings configuration.
    Manages file type restrictions and size limits.
    """
    feature_name = ConfigCategory.UPLOAD.label

    def get(self, request, *args, **kwargs):
        # Get base config
        config_data = ConfigService.get_by_category(ConfigCategory.UPLOAD)

        # Build dynamic upload_file_config
        upload_file_config = {}
        for key, ft in UPLOAD_FILE_CONFIG.items():
            item = ft.copy()
            item['size_value'] = config_data.get(ft['size_key'], ft['default_size'])
            item['type_value'] = config_data.get(ft['type_key'], ft['default_type']).split(',')
            item['key_value'] = _(key)
            upload_file_config[key] = item

        context = {
            'config': config_data,
            'upload_file_config': upload_file_config,
            'title': ConfigCategory.UPLOAD.label,
            'path_rule': list(UploadPathRule),
        }
        return render(request, 'config/upload_setting.html', context)

    def post(self, request, *args, **kwargs):
        data = self._get_cleaned_data(request)
        try:
            if data:
                ConfigService.set_by_category(ConfigCategory.UPLOAD, data)
                messages.success(request, _("Configuration updated successfully."))
        except Exception as e:
            messages.error(request, _("Failed to save configuration: %(error)s") % {"error": e})

        return self.get(request, *args, **kwargs)


class EmailConfigView(BaseAdminView):
    """
    Email server and template configuration.
    Manages SMTP settings and email templates.
    """
    feature_name = ConfigCategory.EMAIL.label

    def get(self, request, *args, **kwargs):
        config_data = ConfigService.get_by_category(ConfigCategory.EMAIL)
        template_data = ConfigService.get_by_category(ConfigCategory.EMAIL_TEMPLATE)

        context = {
            'config': config_data,
            'config_email_template': template_data,
            'title': ConfigCategory.EMAIL.label,
        }

        return render(request, 'config/email_settings.html', context)

    def post(self, request, *args, **kwargs):
        try:
            data = self._get_cleaned_data(request)
            action = data.pop('action', '')

            match action:
                case 'reset':
                    self._handle_reset()
                    messages.success(request, _("Email configuration has been reset."))
                case 'email_base':
                    self._handle_email_base(data)
                    messages.success(request, _("Email base settings updated."))
                case 'email_template':
                    self._handle_email_template(data)
                    messages.success(request, _("Email template updated."))
                case 'test':
                    return self._handle_test(data)
                case 'test_template':
                    return self._handle_test_template(data)
                case _:
                    messages.error(request, _("Invalid action."))
        except Exception as e:
            messages.error(request, _("Failed to process request: %(error)s") % {"error": e})

        return self.get(request, *args, **kwargs)

    def _handle_reset(self):
        ConfigService.delete(category=ConfigCategory.EMAIL)

    def _handle_email_base(self, data):
        # Normalize checkbox values
        for key in ['email_use_ssl', 'email_use_tls']:
            data.setdefault(key, 'off')

        timeout = data.get('email_timeout')
        if not timeout:
            data.pop('email_timeout', None)

        ConfigService.set_by_category(ConfigCategory.EMAIL, data)

    @staticmethod
    def _handle_email_template(data):
        ConfigService.set_by_category(ConfigCategory.EMAIL_TEMPLATE, data)

    @staticmethod
    def _handle_test(data):
        to = data.get('test_receiver', '').strip()
        subject = data.get('test_subject', '').strip()
        content = data.get('test_content', '')

        if not to:
            return api.error(ErrorCode.BAD_REQUEST, _('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid email address'))

        try:
            email = EmailService()
            res = email.send(to, subject, content)
            if res > 0:
                return api.success(_('Successfully sent email.'), {'has_send': res})

            return api.error(ErrorCode.BAD_REQUEST, _('Failed to send email.'))
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))

    @staticmethod
    def _handle_test_template(data):
        to = data.get('test_receiver', '').strip()
        raw_vars = data.get('test_variables', '').strip()

        if not to:
            return api.error(ErrorCode.BAD_REQUEST, _('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid email address'))

        try:
            variables = json.loads(raw_vars) if raw_vars else {}
        except JSONDecodeError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid JSON format for variables.'))

        try:
            email = EmailService()
            res = email.send_with_template(to, variables)
            if res > 0:
                return api.success(_('Successfully sent email.'), {'has_send': res})
            else:
                return api.error(ErrorCode.BAD_REQUEST, _('Failed to send email.'))
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))


class FileManagementView(BaseAdminView):
    superuser_only = True

    def get(self, request, *args, **kwargs):
        current_page = request.GET.get('page', 1)
        context = UploadService.list(current_page)
        context.update({'title': ConfigCategory.FILE.label})
        return render(request, 'config/files.html', context)


class NavItemView(BaseAdminView):
    """
    Handle CRUD operations for navigation items within a given navigation group.
    This view assumes 'view' permission is sufficient for access.
    """
    permission_required = f"{NavItem._meta.app_label}.view_{NavItem._meta.model_name}"

    def get(self, request, *args, **kwargs):
        """
        Render navigation item form for creation or editing.
        """
        nav_id = kwargs.get('nav_id')
        nav_item_id = kwargs.get('nav_item_id', 0)

        # Fetch main navigation object or 404
        nav = get_object_or_404(Nav, id=nav_id)
        # Retrieve existing items for sidebar or context list
        nav_items = NavService.get_items(nav)

        # Determine edit or add mode
        if nav_item_id:
            nav_item = get_object_or_404(NavItem, id=nav_item_id, nav=nav)
            action = _('Edit')
        else:
            nav_item = NavItem(nav=nav)
            action = _('Add')

        context = {
            'title': f"{action} {_('Nav Item')}",
            'nav': nav,
            'nav_id': nav_id,
            'nav_item_id': nav_item_id,
            'nav_item': nav_item,
            'nav_items': nav_items,
            'target': TargetChoices,
        }
        return render(request, 'config/navitem_form.html', context)

    def post(self, request, *args, **kwargs):
        """
        Create or update a navigation item.
        """
        nav_id = kwargs.get('nav_id')
        nav_item_id = kwargs.get('nav_item_id')

        # Ensure related navigation exists
        nav = get_object_or_404(Nav, id=nav_id)
        nav_item = get_object_or_404(NavItem, id=nav_item_id, nav=nav) if nav_item_id else None

        # Prepare POST data and enforce relationship
        post_data = request.POST.copy()
        post_data['nav'] = nav.id

        form = NavItemForm(post_data, nav_id=nav.id, instance=nav_item)
        if form.is_valid():
            form.save()
            # Support "Save and add another" feature
            if 'add_another' in request.POST:
                return redirect(request.path)
            # Redirect to navigation item list
            redirect_url = reverse('admin:cmfadmin:nav_items_edit', kwargs={'pk': nav.id})
            return redirect(redirect_url)

        # If invalid, re-render with form errors
        nav_items = NavService.get_items(nav)
        context = {
            'nav': nav,
            'nav_item': nav_item,
            'nav_id': nav_id,
            'nav_item_id': nav_item_id,
            'nav_items': nav_items,
            'form': form,
            'target': TargetChoices,
        }
        return render(request, 'config/navitem_form.html', context)

    def delete(self, request, *args, **kwargs):
        """
        Delete a navigation item only if it has no child items.
        Return JSON response for frontend AJAX handling.
        """
        nav_item_id = kwargs.get('nav_item_id')
        if not nav_item_id:
            return api.error(ErrorCode.BAD_REQUEST, _('Missing navigation item ID.'))

        try:
            nav_item = NavItem.objects.get(pk=nav_item_id)
        except NavItem.DoesNotExist:
            return api.error(ErrorCode.NOT_FOUND, _('Node does not exist.'))

        # Prevent deletion if children exist
        if nav_item.children.exists():
            return api.error(
                ErrorCode.BAD_REQUEST,
                _('This node has child items and cannot be deleted. Please delete child items first.')
            )

        # Attempt to delete safely
        try:
            nav_item.delete()
            return api.success(_('Deleted successfully.'))
        except Exception as e:
            # Catch any unexpected errors (e.g., DB constraints)
            return api.error(ErrorCode.SERVER_ERROR, _('Failed to delete item: ') + str(e))


class SpriteManagerView(BaseAdminView):
    template_name = 'config/sprite_manager.html'
    add_template_name = 'config/sprite_add.html'
    feature_name = ConfigCategory.ICONS.label

    @staticmethod
    def _get_custom_sprite_file():
        """
        Get validated custom sprite file path with security checks
        """
        custom_sprite_path = getattr(settings, 'CUSTOM_SPRITE_FILE', CUSTOM_SPRITE_FILE)

        # Prevent relative path traversal
        if '..' in os.path.normpath(custom_sprite_path).split(os.sep):
            raise SuspiciousFileOperation("Relative path traversal is not allowed")

        static_dir = get_static_dir()
        full_path = os.path.abspath(os.path.join(static_dir, custom_sprite_path))

        # Ensure the final path is inside static dir
        if not os.path.commonpath([static_dir]) == os.path.commonpath([static_dir, full_path]):
            raise SuspiciousFileOperation(f"Invalid path: {full_path} not in {static_dir}")

        return full_path

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        symbol_id = request.GET.get('symbol_id')

        if action == 'add':
            return render(request, self.add_template_name, {'title': _('Add Sprite Icon')})
        elif action == 'edit':
            context = {'title': _('Edit Sprite Icon'), 'symbol_id': symbol_id, 'action': action}
            return render(request, self.add_template_name, context)

        # Load system sprite file
        sprite_file = finders.find('admin/svg/sprite.svg')
        # Load custom sprite file if configured
        custom_sprite_file = self._get_custom_sprite_file()

        icons, custom_icons = [], []

        # Load the built-in system sprite file and retrieve its symbol list
        try:
            icons = SpriteManager(sprite_file).list()
        except SpriteError as e:
            messages.warning(request, _("Failed to load system sprite: %(error)s") % {"error": e})

        # If a custom sprite file is configured and exists, load its symbols as well
        if custom_sprite_file:
            try:
                custom_icons = SpriteManager(custom_sprite_file).list()
            except SpriteError as e:
                messages.warning(request, _("Failed to load custom sprite: %(error)s") % {"error": e})

        context = {
            'title': 'Sprite Manager',
            'icons': icons,
            'custom_icons': custom_icons,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle adding or updating a custom sprite via form submission.
        Form submit → render template on error, redirect on success.
        """
        symbol_id = request.POST.get('symbol_id', '').strip()
        svg_code = request.POST.get('svg_code', '').strip()
        context = {'symbol_id': symbol_id, 'svg_code': svg_code, }

        # Required fields validation
        if not symbol_id or not svg_code:
            messages.warning(request, _('Symbol ID and SVG code are required.'))
            return render(request, self.add_template_name, context)

        try:
            manager = SpriteManager(self._get_custom_sprite_file())

            # Add or update the icon in the sprite
            if manager.has(symbol_id):
                manager.update(symbol_id, svg_code)
                messages.success(request, _("Icon '%(id)s' has been updated successfully.") % {'id': symbol_id})
            else:
                manager.add(symbol_id, svg_code)
                messages.success(request, _("New icon '%(id)s' has been added successfully.") % {'id': symbol_id})

            # On success → redirect to the sprite manager page
            return redirect(reverse('admin:cmfadmin:icons_manage'))
        except Exception as e:
            # On error → stay on the current add page with error message
            messages.error(request, _("Error: %(error)s") % {'error': e})
            return render(request, self.add_template_name, context)

    def delete(self, request, *args, **kwargs):
        """
        Handle deleting a custom sprite via AJAX.
        Returns JSON response.
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid JSON format.'))

        symbol_id = data.get('symbol_id', '')
        if not symbol_id:
            return api.error(ErrorCode.BAD_REQUEST, _('Symbol ID is required.'))

        try:
            manager = SpriteManager(self._get_custom_sprite_file())
            if manager.has(symbol_id):
                manager.remove(symbol_id)
                return api.success(_('Deleted successfully.'))
            return api.error(ErrorCode.NOT_FOUND, _('Symbol ID not found.'))
        except SpriteError as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error: %(error)s') % {'error': e})


class UploadFileView(View):
    """Handle file upload and deletion."""

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        file_type_str = request.POST.get('file_type')

        if not uploaded_file or not file_type_str:
            return api.error(ErrorCode.BAD_REQUEST, _('Missing file or file_type'))

        try:
            file_type = FileType(file_type_str)
        except ValueError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid file_type'))

        try:
            uploader = UploadService()
            info = uploader.save(uploaded_file, file_type, request.user)
            return api.success(_('Upload successful.'), info.to_dict())
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Upload failed: %(error)s') % {"error": e})

    def delete(self, request, *args, **kwargs):
        """
        Delete file. Expects 'path' parameter in query string or request body JSON.
        """
        # Prefer request body JSON if available
        try:
            data = json.loads(request.body)
            file_path = data.get('path')
        except (json.JSONDecodeError, TypeError):
            file_path = request.GET.get('path')

        if not file_path:
            return api.error(ErrorCode.BAD_REQUEST, _("Missing file path"))

        try:
            if UploadService.delete(file_path):
                return api.success(_("Delete successful."))
            else:
                return api.error(ErrorCode.NOT_FOUND, _("File not found"))
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Delete failed: %(error)s') % {"error": e})


class UserProfile(View):
    """Handle user profile update and display."""
    template_name = 'admin/auth/user/profile.html'

    def get(self, request, *args, **kwargs):
        """Render profile page with current user data."""
        context = {
            'user': request.user,
            'title': _('User Profile'),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Update basic user information: first_name, last_name, email.
        Uses minimal validation and consistent toast-style feedback.
        """
        base_fields = ['first_name', 'last_name', 'email']
        updated = False

        # Cleanly assign posted values
        for field in base_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(request.user, field, value.strip())
                updated = True

        if not updated:
            messages.info(request, _('No changes detected.'))
        else:
            try:
                request.user.full_clean()  # Basic field validation (email format etc.)
                request.user.save(update_fields=base_fields)
                messages.success(request, _("Profile updated successfully."))
            except Exception as e:
                messages.error(request, _("Failed to save profile: %(error)s") % {'error': e})

        return render(request, self.template_name, {'user': request.user})


@permission_required(f"{NavItem._meta.app_label}.view_{NavItem._meta.model_name}")
def nav_items_edit(request, pk):
    nav = Nav.objects.get(pk=pk)
    nav_items = NavService.get_items(nav)

    context = {
        'title': ConfigCategory.NAV.label,
        'nav': nav,
        'nav_items': nav_items,
    }
    return render(request, 'config/navigation.html', context)


@permission_required(superuser_only=True)
def sync_menu(request):
    """
    Sync all admin menus (superuser only).
    """
    result = AdminMenuManager.synchronize_menu(MenuSyncMode.SYNC_ALL, request.user)
    return render(request, 'config/sync_menu.html', {'result': result})
