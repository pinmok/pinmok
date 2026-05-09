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
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, resolve, Resolver404
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.http import require_GET

from djangocmf.cmfadmin.constants import CUSTOM_SPRITE_FILE, CMF_ICON_PREFIX, CMF_SPRITE_FILE
from djangocmf.cmfadmin.enums import FileType, ConfigCategory
from djangocmf.cmfadmin.models import UrlAlias
from djangocmf.cmfadmin.service.email import EmailService, EmailValueError
from djangocmf.cmfadmin.service.menu import AdminMenuManager
from djangocmf.cmfadmin.service.menu import MenuSyncMode
from djangocmf.cmfadmin.service.navigation import NavService
from djangocmf.cmfadmin.service.theme import ThemeService, ThemeServiceError
from djangocmf.cmfadmin.service.upload import UploadService
from djangocmf.core import api
from djangocmf.core.api import ErrorCode
from djangocmf.core.libs.sprite import SpriteManager, SpriteError
from djangocmf.core.mixins import CMFPermissionMixin


def license_page(request):
    """Serve the License information page."""
    return TemplateResponse(request, 'pages/license.html')


def sync_menu(request):
    """
    Sync all admin menus (superuser only).
    """
    result = AdminMenuManager.synchronize_menu(MenuSyncMode.SYNC_ALL, request.user)
    return render(request, 'config/sync_menu.html', {'result': result})


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
        except EmailValueError as e:
            return api.error(ErrorCode.BAD_REQUEST, str(e))
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
        except EmailValueError as e:
            return api.error(ErrorCode.BAD_REQUEST, str(e))
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
            service = UploadService(file_type, user=request.user)
            resource = service.save(uploaded_file)
            return api.success(_('Upload successful.'), {
                'id': resource.id,
                'url': resource.url,
                'original_name': resource.original_name,
                'size': resource.size,
            })
        except ValidationError as e:
            return api.error(ErrorCode.VALIDATION_ERROR, e.message)
        except Exception as e:
            return api.error(ErrorCode.SERVER_ERROR, _('Upload failed: %(error)s') % {'error': e})


def alias_resolver(request, alias):
    """
    Resolve a URL alias and forward the request to the corresponding view internally.

    Looks up the given alias in the UrlAlias table. If a matching active alias is found,
    resolves the target URL to its view function and forwards the request directly,
    without redirecting the browser. The visitor's address bar keeps showing the alias URL.

    Raises Http404 if the alias does not exist, is inactive, or the target URL does not
    resolve to a known view.
    """
    # Look up the alias in the database
    try:
        url_alias = UrlAlias.objects.get(alias=alias, is_active=True)
    except UrlAlias.DoesNotExist:
        raise Http404

    # Resolve the target URL to a view function
    try:
        match = resolve(url_alias.target)
    except Resolver404:
        raise Http404

    # Forward the request to the resolved view internally
    return match.func(request, *match.args, **match.kwargs)


class ThemeView:
    @staticmethod
    def theme_list(request):
        """Render the theme management list page."""
        themes = ThemeService.scan()
        return TemplateResponse(request, 'theme/list.html', {
            'title': _('List of themes'),
            'subtitle': _('Theme Management'),
            'themes': themes,
        })

    @staticmethod
    def install(request, directory: str):
        """Install a theme from the given directory."""
        try:
            ThemeService.install(directory)
            messages.success(request, _('Theme installed successfully.'))
        except ThemeServiceError as e:
            messages.error(request, str(e))
        return redirect(reverse('admin:cmfadmin:theme_list'))

    @staticmethod
    def uninstall(request, theme_id: int):
        """Uninstall a theme by its primary key."""
        try:
            ThemeService.uninstall(theme_id)
            messages.success(request, _('Theme uninstalled successfully.'))
        except ThemeServiceError as e:
            messages.error(request, str(e))
        return redirect(reverse('admin:cmfadmin:theme_list'))

    @staticmethod
    def activate(request, theme_id: int):
        """Activate a theme by its primary key."""
        try:
            ThemeService.activate(theme_id)
            messages.success(request, _('Theme activated successfully.'))
        except ThemeServiceError as e:
            messages.error(request, str(e))
        return redirect(reverse('admin:cmfadmin:theme_list'))

    @staticmethod
    def reset(request, theme_id: int):
        """Reset a theme to its default configuration."""
        try:
            ThemeService.reset(theme_id)
            messages.success(request, _('Theme reset successfully.'))
        except ThemeServiceError as e:
            messages.error(request, str(e))
        return redirect(reverse('admin:cmfadmin:theme_list'))

    @staticmethod
    def config(request, theme_id: int):
        """Render the theme configuration page."""
        template_id = request.GET.get('template')
        ctx = ThemeService.get_config_context(theme_id, int(template_id) if template_id else None)
        return TemplateResponse(request, 'theme/config.html', {
            'title': ctx['theme'].name,
            'subtitle': _('Theme Configuration'),
            'ctx': ctx,
        })


class ThemeConfigView(View):
    """Theme configuration editing view. GET renders the form, POST saves and redirects back."""

    def get(self, request, theme_id: int):
        template_id = request.GET.get('template')
        ctx = ThemeService.get_config_context(
            theme_id,
            int(template_id) if template_id else None,
        )
        return TemplateResponse(request, 'theme/config.html', {
            'title': ctx['theme'].name,
            'subtitle': _('Theme Configuration'),
            **ctx,
        })

    def post(self, request, theme_id: int):
        template_id_raw = request.POST.get('template_id')
        template_id = int(template_id_raw) if template_id_raw else None

        var_definitions = ThemeService.get_var_definitions(theme_id, template_id)
        submitted = ThemeService.collect_submitted(request.POST, var_definitions)

        if template_id:
            ThemeService.save_template_config(int(template_id), submitted)
        else:
            ThemeService.save_config(theme_id, submitted)

        redirect_url = request.path
        if template_id:
            redirect_url += f'?template={template_id}'
        return redirect(redirect_url)


@require_GET
def nav_parent_choices(request):
    """
    Return parent choices for the Nav parent field.
    Filtered by group, excluding the specified node and its descendants.
    Used by the NavAdmin parent field AJAX update.
    """
    group = request.GET.get('group', '')
    if not group:
        return JsonResponse({'choices': []})

    exclude_id = request.GET.get('exclude_id')
    items = NavService.get_items(
        group,
        exclude_id=int(exclude_id) if exclude_id else None
    )
    choices = [{'id': node.id, 'label': label} for node, label in items]
    return JsonResponse({'choices': choices})
