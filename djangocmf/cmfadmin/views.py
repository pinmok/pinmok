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
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.shortcuts import render, redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from djangocmf.cmfadmin.constants import CUSTOM_SPRITE_FILE, CMF_ICON_PREFIX, CMF_SPRITE_FILE
from djangocmf.cmfadmin.enums import FileType, ConfigCategory, TargetChoices
from djangocmf.cmfadmin.forms.forms import NavItemForm
from djangocmf.cmfadmin.models import Nav, NavItem
from djangocmf.cmfadmin.service.email import EmailService
from djangocmf.cmfadmin.service.menu import AdminMenuManager
from djangocmf.cmfadmin.service.menu import MenuSyncMode
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.service.upload import UploadService
from djangocmf.core import api
from djangocmf.core.api import ErrorCode
from djangocmf.core.libs.sprite import SpriteManager, SpriteError
from djangocmf.core.mixins import CMFPermissionMixin
from djangocmf.core.utils.tools import to_compact_case


def license_page(request):
    """Serve the License information page."""
    return render(request, 'pages/license.html')


class BaseAdminView(View):
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


class TestEmailView(View):
    """
    Handles test email sending requests from the admin email config panel.

    Supports two actions via POST:
      - 'test'          : Send a plain text email to verify SMTP settings.
      - 'test_template' : Send a templated email to verify template rendering.
    """

    @staticmethod
    def _validate_receiver(to: str):
        """Validate the recipient address. Returns an error response or None."""
        if not to:
            return api.error(ErrorCode.BAD_REQUEST, _('Recipient address is required.'))
        try:
            validate_email(to)
        except ValidationError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid email address.'))
        return None

    @staticmethod
    def _handle_test(data: dict):
        """Send a plain text test email."""
        to = data.get('test_receiver', '').strip()
        subject = data.get('test_subject', '').strip()
        content = data.get('test_content', '')

        error = TestEmailView._validate_receiver(to)
        if error:
            return error

        try:
            email = EmailService()
            res = email.send(to, subject, content)
            if res > 0:
                return api.success(_('Successfully sent email.'), {'has_send': res})
            return api.error(ErrorCode.BAD_REQUEST, _('Failed to send email.'))
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))

    @staticmethod
    def _handle_test_template(data: dict):
        """Send a templated test email with optional JSON variables."""
        to = data.get('test_receiver', '').strip()
        raw_vars = data.get('test_variables', '').strip()

        error = TestEmailView._validate_receiver(to)
        if error:
            return error

        try:
            variables = json.loads(raw_vars) if raw_vars else {}
        except JSONDecodeError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid JSON format for variables.'))

        try:
            email = EmailService()
            res = email.send_with_template(to, variables)
            if res > 0:
                return api.success(_('Successfully sent email.'), {'has_send': res})
            return api.error(ErrorCode.BAD_REQUEST, _('Failed to send email.'))
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))

    def post(self, request, *args, **kwargs):
        """Dispatch to the appropriate handler based on the 'action' field."""
        action = request.POST.get('action', '').strip()

        match action:
            case 'test':
                return self._handle_test(request.POST)
            case 'test_template':
                return self._handle_test_template(request.POST)
            case _:
                return api.error(ErrorCode.BAD_REQUEST, _('Invalid action.'))


class NavItemView(View):
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


class SpriteManagerView(View):
    template_name = 'config/sprite_manager.html'
    add_template_name = 'config/sprite_add.html'
    feature_name = ConfigCategory.ICONS.label

    @staticmethod
    def _get_custom_sprite_path() -> str:
        """
        Get the relative media path for the custom sprite file.
        Validates against path traversal attempts.

        Returns:
            str: Relative path to the custom sprite file (relative to MEDIA_ROOT).

        Raises:
            SuspiciousFileOperation: If the path contains traversal attempts.
        """
        path = getattr(settings, 'CUSTOM_SPRITE_FILE', CUSTOM_SPRITE_FILE)

        # Prevent path traversal
        if '..' in os.path.normpath(path).split(os.sep):
            raise SuspiciousFileOperation("Relative path traversal is not allowed")

        return path

    @staticmethod
    def _get_or_create_custom_sprite() -> str:
        """
        Get the custom sprite relative path, creating the file if it does not exist.

        Returns:
            str: Relative path to the custom sprite file.

        Raises:
            SuspiciousFileOperation: If the path fails security checks.
            SpriteError: If the file cannot be created.
        """
        path = SpriteManagerView._get_custom_sprite_path()
        if not default_storage.exists(path):
            SpriteManager.create(path)
        return path

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        symbol_id = request.GET.get('symbol_id', '').strip()

        if action == 'add':
            return TemplateResponse(request, self.add_template_name, {
                'title': _('Add Sprite Icon'),
            })

        if action == 'edit':
            if not symbol_id:
                messages.warning(request, _('Symbol ID is required.'))
                return redirect(reverse('admin:cmfadmin:icons_manage'))

            custom_sprite_path = self._get_custom_sprite_path()
            svg_code = ''
            if default_storage.exists(custom_sprite_path):
                try:
                    svg_code = SpriteManager(custom_sprite_path).get(symbol_id)
                except SpriteError as e:
                    messages.warning(request, _("Failed to load symbol: %(error)s") % {"error": e})

            return TemplateResponse(request, self.add_template_name, {
                'title': _('Edit Sprite Icon'),
                'symbol_id': symbol_id,
                'svg_code': svg_code,
                'action': action,
            })

        custom_sprite_path = self._get_custom_sprite_path()

        icons, custom_icons = [], []

        try:
            system_sprite_path = finders.find(CMF_SPRITE_FILE)
            if not system_sprite_path:
                raise SpriteError("System sprite file not found in static files.")
            icons = SpriteManager.list_system_symbols(system_sprite_path)
        except SpriteError as e:
            messages.warning(request, _("Failed to load system sprite: %(error)s") % {"error": e})

        # Custom sprite file may not exist yet, which is normal
        if default_storage.exists(custom_sprite_path):
            try:
                custom_icons = SpriteManager(custom_sprite_path).list_symbols()
            except SpriteError as e:
                messages.warning(request, _("Failed to load custom sprite: %(error)s") % {"error": e})

        return TemplateResponse(request, self.template_name, {
            'title': _('Sprite Manager'),
            'icons': icons,
            'custom_icons': custom_icons,
        })

    def post(self, request, *args, **kwargs):
        """
        Handle adding or updating a custom sprite icon via form submission.
        Renders the form template on error, redirects on success.
        """
        symbol_id = request.POST.get('symbol_id', '').strip()
        svg_code = request.POST.get('svg_code', '').strip()
        original_id = request.POST.get('original_id', '').strip()
        context = {'symbol_id': symbol_id, 'svg_code': svg_code}

        if not symbol_id or not svg_code:
            messages.warning(request, _('Symbol ID and SVG code are required.'))
            return TemplateResponse(request, self.add_template_name, context)

        if symbol_id.startswith(CMF_ICON_PREFIX):
            messages.error(request, _("Symbol ID cannot start with '%(prefix)s'.") % {'prefix': CMF_ICON_PREFIX})
            return TemplateResponse(request, self.add_template_name, context)

        try:
            custom_sprite_path = self._get_or_create_custom_sprite()
            manager = SpriteManager(custom_sprite_path)

            if original_id and manager.has(original_id):
                # Edit mode: remove old symbol, add new one
                manager.remove(original_id)
                manager.add(symbol_id, svg_code)
                messages.success(request, _("Icon '%(id)s' has been updated successfully.") % {'id': symbol_id})
            else:
                # Add mode: symbol_id must not already exist
                if manager.has(symbol_id):
                    manager.update(symbol_id, svg_code)
                    messages.success(request, _("Icon '%(id)s' has been updated successfully.") % {'id': symbol_id})
                else:
                    manager.add(symbol_id, svg_code)
                    messages.success(request, _("New icon '%(id)s' has been added successfully.") % {'id': symbol_id})

            return redirect(reverse('admin:cmfadmin:icons_manage'))
        except Exception as e:
            messages.error(request, _("Error: %(error)s") % {'error': e})
            return TemplateResponse(request, self.add_template_name, context)

    def delete(self, request, *args, **kwargs):
        """
        Handle deleting a custom sprite icon via AJAX.
        Returns JSON response.
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid JSON format.'))

        symbol_id = data.get('symbol_id', '').strip()
        if not symbol_id:
            return api.error(ErrorCode.BAD_REQUEST, _('Symbol ID is required.'))

        custom_sprite_path = self._get_custom_sprite_path()
        if not default_storage.exists(custom_sprite_path):
            return api.error(ErrorCode.NOT_FOUND, _('Symbol ID not found.'))

        try:
            manager = SpriteManager(custom_sprite_path)
            if not manager.has(symbol_id):
                return api.error(ErrorCode.NOT_FOUND, _('Symbol ID not found.'))
            manager.remove(symbol_id)
            return api.success(_('Deleted successfully.'))
        except SpriteError as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Error: %(error)s') % {'error': e})


class UploadFileView(CMFPermissionMixin, View):
    """
    AJAX-only file upload endpoint.

    Accepts:
      POST multipart/form-data
        file      — the uploaded file
        file_type — one of: image, audio, video, document, archive

    Returns:
      200 { code, message, data: { path, media_path, ... } }
      400 on missing or invalid parameters
      422 on validation failure (file type or size not allowed)
      500 on unexpected error
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        file_type_str = request.POST.get('file_type')

        if not uploaded_file or not file_type_str:
            return api.error(ErrorCode.BAD_REQUEST, _('Missing file or file_type.'))

        try:
            file_type = FileType(file_type_str)
        except ValueError:
            return api.error(ErrorCode.BAD_REQUEST, _('Invalid file_type: %(value)s') % {'value': file_type_str})

        try:
            service = UploadService(file_type)
            result = service.save(uploaded_file)
            return api.success(_('Upload successful.'), result.to_dict())
        except ValidationError as e:
            return api.error(ErrorCode.VALIDATION_ERROR, e.message)
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Upload failed: %(error)s') % {'error': e})


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


def nav_items_edit(request, pk):
    nav = Nav.objects.get(pk=pk)
    nav_items = NavService.get_items(nav)

    context = {
        'title': ConfigCategory.NAV.label,
        'nav': nav,
        'nav_items': nav_items,
    }
    return render(request, 'config/navigation.html', context)


def sync_menu(request):
    """
    Sync all admin menus (superuser only).
    """
    result = AdminMenuManager.synchronize_menu(MenuSyncMode.SYNC_ALL, request.user)
    return render(request, 'config/sync_menu.html', {'result': result})
