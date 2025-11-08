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

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from cmfadmin.constants import CUSTOM_SPRITE_FILE, UPLOAD_FILE_CONFIG
from cmfadmin.enums import ConfigCategory, TargetChoices, FileType, ErrorCode, MenuSyncMode
from cmfadmin.forms import NavItemForm
from cmfadmin.libs import SpriteManager
from cmfadmin.libs.sprite import SpriteError
from cmfadmin.libs.upload import UploadPathRule
from cmfadmin.menus import AdminMenuManager
from cmfadmin.models import Nav, NavItem
from cmfadmin.service.authorization import PermissionRequiredMixin, permission_required
from cmfadmin.service.config import ConfigService
from cmfadmin.service.email import EmailService
from cmfadmin.service.navigation import NavService
from cmfadmin.service.upload import UploadService
from cmfadmin.utils.helper import get_static_dir, api_response
from cmfadmin.utils.tools import to_compact_case


class ConfigView(PermissionRequiredMixin, View):
    category: ConfigCategory | None = None
    extra_categories: list[ConfigCategory] | None = None
    template_name: str | None = None
    extra_context: dict | None = None
    exclude_keys: list[str] = ['csrfmiddlewaretoken']

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Automatically generate permission_required based on category.
        """
        super().__init_subclass__(**kwargs)
        if getattr(cls, "category", None):
            safe_title = to_compact_case(cls.category.label)  # type: ignore[arg-type]
            cls.permission_required = f"view_{safe_title}"

    def _get_exclude_keys(self) -> list[str]:
        """
        Return merged exclude_keys (base + subclass).
        """
        base = ConfigView.exclude_keys
        current = getattr(self, 'exclude_keys', [])
        return list(dict.fromkeys(base + current))

    def _get_cleaned_data(self, request) -> dict[str, str]:
        """
        Filter out unwanted POST keys and trim values.
        Handles multi-value POST fields by taking the first value.
        """
        exclude = self._get_exclude_keys()
        return {
            key: (value[0] if isinstance(value, list) else value).strip()
            for key, value in request.POST.lists()
            if key not in exclude
        }

    def _get_context_data(self, extra: dict | None = None) -> dict:
        """
        Build context with main and extra categories, static and dynamic extra context.
        Each request gets independent dict to avoid shared mutable objects.
        """
        context: dict = {}

        # Main + extra categories
        categories = [self.category] if self.category else []
        if self.extra_categories:
            categories.extend(self.extra_categories)

        for cat in categories:
            key = 'config' if cat == self.category else f'config_{cat.name.lower()}'
            context[key] = ConfigService.get_by_category(cat)

        # Static extra context
        context.update(self.extra_context or {})

        # Dynamic extra context
        if extra:
            context.update(extra)

        return context

    def _handle_file_upload(self, request, field_name: str, file_type: FileType) -> str | None:
        """
        Handle a single file upload for a given POST field safely.
        """
        file = request.FILES.get(field_name)
        if not file:
            return None

        try:
            service = UploadService()
            result = service.save(file, file_type, request.user)
            return result.path
        except Exception as e:
            messages.error(request, _("Failed to upload '%(name)s': %(error)s") % {
                "name": file.name,
                "error": e
            })
            return None

    def get(self, request, *args, **kwargs):
        """
        Render configuration template with context data.
        """
        try:
            context = self._get_context_data()
        except Exception as e:
            messages.error(request, _("Failed to load configuration: %(error)s") % {"error": e})
            context = {}

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Save configuration form submission safely.
        """
        try:
            data = self._get_cleaned_data(request)
            if data:
                ConfigService.set_by_category(self.category, data)
                messages.success(request, _("Configuration updated successfully."))
            else:
                messages.warning(request, _("No valid data submitted."))
        except Exception as e:
            messages.error(request, _("Failed to save configuration: %(error)s") % {"error": e})

        # Always render page instead of redirect to avoid loop and keep messages
        try:
            context = self._get_context_data(extra={'post_data': request.POST.dict()})
        except Exception:
            context = {}
        return render(request, self.template_name, context)


class SiteInfoView(ConfigView):
    category = ConfigCategory.SITE
    template_name = 'config/site_info.html'
    extra_context = {
        'title': ConfigCategory.SITE.label,
    }

    def post(self, request, *args, **kwargs):
        logo_path = self._handle_file_upload(request, 'site_logo', FileType.IMAGE)
        if logo_path:
            request.POST = request.POST.copy()
            request.POST['site_logo'] = logo_path

        return super().post(request, *args, **kwargs)


class UploadSettingView(ConfigView):
    category = ConfigCategory.UPLOAD
    template_name = 'config/upload_setting.html'
    extra_context = {
        'title': ConfigCategory.UPLOAD.label,
        'path_rule': list(UploadPathRule),
    }

    def get(self, request, *args, **kwargs):
        # Get base config
        config_data = ConfigService.get_by_category(self.category)

        # Build dynamic upload_file_config
        upload_file_config = {}
        for key, ft in UPLOAD_FILE_CONFIG.items():
            item = ft.copy()
            item['size_value'] = config_data.get(ft['size_key'], ft['default_size'])
            item['type_value'] = config_data.get(ft['type_key'], ','.join(ft['default_type'])).split(',')
            item['key_value'] = _(key)
            upload_file_config[key] = item

        # Pass as dynamic context (avoid mutating class-level dict)
        extra = {'upload_file_config': upload_file_config}
        context = self._get_context_data(extra)
        return render(request, self.template_name, context)


class EmailConfigView(ConfigView):
    category = ConfigCategory.EMAIL
    extra_categories = [ConfigCategory.EMAIL_TEMPLATE]
    template_name = 'config/email_settings.html'
    extra_context = {
        'title': ConfigCategory.EMAIL.label,
    }

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

        try:
            context = self._get_context_data(extra={'post_data': request.POST.dict()})
        except Exception:
            context = {}
        return render(request, self.template_name, context)

    def _handle_reset(self):
        ConfigService.delete(category=self.category)

    def _handle_email_base(self, data):
        # Normalize checkbox values
        for key in ['email_use_ssl', 'email_use_tls']:
            data.setdefault(key, 'off')

        timeout = data.get('email_timeout')
        if not timeout:
            data.pop('email_timeout', None)

        ConfigService.set_by_category(self.category, data)

    @staticmethod
    def _handle_email_template(data):
        ConfigService.set_by_category(ConfigCategory.EMAIL_TEMPLATE, data)

    @staticmethod
    def _handle_test(data):
        to = data.get('test_receiver', '').strip()
        subject = data.get('test_subject', '').strip()
        content = data.get('test_content', '')

        if not to:
            return api_response(ErrorCode.BAD_REQUEST, _('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api_response(ErrorCode.BAD_REQUEST, _('Invalid email address'))

        try:
            email = EmailService()
            res = email.send(to, subject, content)
            if res > 0:
                return api_response(ErrorCode.SUCCESS, _('Successfully sent email.'), {'has_send': res})
            else:
                return api_response(ErrorCode.ERROR, _('Failed to send email.'))
        except Exception as e:
            return api_response(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))

    @staticmethod
    def _handle_test_template(data):
        to = data.get('test_receiver', '').strip()
        raw_vars = data.get('test_variables', '').strip()

        if not to:
            return api_response(ErrorCode.BAD_REQUEST, _('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api_response(ErrorCode.BAD_REQUEST, _('Invalid email address'))

        try:
            variables = json.loads(raw_vars) if raw_vars else {}
        except JSONDecodeError:
            return api_response(ErrorCode.BAD_REQUEST, _('Invalid JSON format for variables.'))

        try:
            email = EmailService()
            res = email.send_with_template(to, variables)
            if res > 0:
                return api_response(ErrorCode.SUCCESS, _('Successfully sent email.'), {'has_send': res})
            else:
                return api_response(ErrorCode.ERROR, _('Failed to send email.'))
        except Exception as e:
            return api_response(ErrorCode.SERVER_ERROR, _('Error while sending email: ') + str(e))


class FileManagementView(PermissionRequiredMixin, View):
    superuser_only = True
    template_name = 'config/files.html'
    extra_context = {
        'title': ConfigCategory.FILE.label,
    }

    def get(self, request, *args, **kwargs):
        current_page = request.GET.get('page', 1)
        context = UploadService.list(current_page)
        context.update(self.extra_context)
        return render(request, self.template_name, context)


class NavItemView(PermissionRequiredMixin, View):
    """
    Handle CRUD operations for navigation items within a given navigation group.
    This view assumes 'view' permission is sufficient for access.
    """
    template_name = 'config/navitem_form.html'
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
        return render(request, self.template_name, context)

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
            redirect_url = reverse('admin:nav_items_edit', kwargs={'pk': nav.id})
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
        return render(request, self.template_name, context)

    def delete(self, request, *args, **kwargs):
        """
        Delete a navigation item only if it has no child items.
        Return JSON response for frontend AJAX handling.
        """
        nav_item_id = kwargs.get('nav_item_id')
        if not nav_item_id:
            return api_response(ErrorCode.BAD_REQUEST, _('Missing navigation item ID.'))

        try:
            nav_item = NavItem.objects.get(pk=nav_item_id)
        except NavItem.DoesNotExist:
            return api_response(ErrorCode.NOT_FOUND, _('Node does not exist.'))

        # Prevent deletion if children exist
        if nav_item.children.exists():
            return api_response(
                ErrorCode.BAD_REQUEST,
                _('This node has child items and cannot be deleted. Please delete child items first.')
            )

        # Attempt to delete safely
        try:
            nav_item.delete()
            return api_response(ErrorCode.SUCCESS, _('Deleted successfully.'))
        except Exception as e:
            # Catch any unexpected errors (e.g., DB constraints)
            return api_response(ErrorCode.SERVER_ERROR, _('Failed to delete item: ') + str(e))


class SpriteManagerView(PermissionRequiredMixin, View):
    template_name = 'config/sprite_manager.html'
    add_template_name = 'config/sprite_add.html'
    permission_required = 'view_iconsmanagement'

    @staticmethod
    def _get_custom_sprite_file():
        """
        Get validated custom sprite file path with security checks
        """
        custom_sprite_path = getattr(settings, 'CUSTOM_SPRITE_FILE', CUSTOM_SPRITE_FILE)

        # Prevent relative path traversal
        if '..' in os.path.normpath(custom_sprite_path).split(os.sep):
            raise SuspiciousFileOperation(_("Relative path traversal is not allowed"))

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
            context = {'title': _('Edit Sprite Icon'), 'symbol_id': symbol_id}
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
            'title': _('Sprite Manager'),
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
            return redirect(reverse('admin:icons_manage'))
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
            return api_response(ErrorCode.BAD_REQUEST, _('Invalid JSON format.'))

        symbol_id = data.get('symbol_id', '')
        if not symbol_id:
            return api_response(ErrorCode.BAD_REQUEST, _('Symbol ID is required.'))

        try:
            manager = SpriteManager(self._get_custom_sprite_file())
            if manager.has(symbol_id):
                manager.remove(symbol_id)
                return api_response(ErrorCode.SUCCESS, _('Deleted successfully.'))
            return api_response(ErrorCode.NOT_FOUND, _('Symbol ID not found.'))
        except SpriteError as e:
            return api_response(ErrorCode.SERVER_ERROR, _('Error: %(error)s') % {'error': e})


class UploadFileView(View):
    """Handle file upload and deletion."""

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        file_type_str = request.POST.get('file_type')

        if not uploaded_file or not file_type_str:
            return api_response(ErrorCode.BAD_REQUEST, _('Missing file or file_type'))

        try:
            file_type = FileType(file_type_str)
        except ValueError:
            return api_response(ErrorCode.BAD_REQUEST, _('Invalid file_type'))

        try:
            uploader = UploadService()
            info = uploader.save(uploaded_file, file_type, request.user)
            return api_response(ErrorCode.SUCCESS, _('Upload successful.'), info.to_dict())
        except Exception as e:
            return api_response(ErrorCode.SERVER_ERROR, _('Upload failed: %(error)s') % {"error": e})

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
            return api_response(ErrorCode.BAD_REQUEST, _("Missing file path"))

        try:
            if UploadService.delete(file_path):
                return api_response(ErrorCode.SUCCESS, _("Delete successful."))
            else:
                return api_response(ErrorCode.NOT_FOUND, _("File not found"))
        except Exception as e:
            return api_response(ErrorCode.SERVER_ERROR, _('Delete failed: %(error)s') % {"error": e})


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
