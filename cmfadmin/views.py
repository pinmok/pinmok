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
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext, gettext_lazy as _
from django.views import View

from cmfadmin.constants import CUSTOM_SPRITE_FILE, UPLOAD_FILE_CONFIG
from cmfadmin.enums import ConfigCategory, MenuSyncMode, TargetChoices, FileType
from cmfadmin.forms import NavItemForm
from cmfadmin.libs import SpriteManager
from cmfadmin.libs.sprite import SpriteError
from cmfadmin.libs.upload import UploadPathRule
from cmfadmin.menus import AdminMenuManager
from cmfadmin.models import Nav, NavItem
from cmfadmin.service.config import ConfigService
from cmfadmin.service.email import EmailService
from cmfadmin.service.navigation import NavService
from cmfadmin.service.upload import UploadService
from cmfadmin.utils.helper import get_static_dir, api_response


class ConfigView(View):
    category = None
    template_name = None
    extra_context = None
    exclude_keys = ['csrfmiddlewaretoken']

    def _get_cleaned_data(self, request):
        """Filter out unwanted keys like csrfmiddlewaretoken."""
        data = {}
        exclude = self._get_exclude_keys()
        for key, value in request.POST.lists():
            if key in exclude:
                continue
            if len(value) == 1:
                # single value, save as string
                data[key] = value[0]
            else:
                # multi value, join as comma-separated string
                data[key] = ",".join(value)
        return data

    def _get_exclude_keys(self):
        """Return merged exclude_keys (base + subclass)."""
        base = ConfigView.exclude_keys
        current = getattr(self, 'exclude_keys', [])
        return list(dict.fromkeys(base + current))

    def get(self, request, *args, **kwargs):
        config_data = ConfigService.get_by_category(self.category)
        context = {
            'config': config_data,
        }
        if self.extra_context:
            context.update(self.extra_context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        data = self._get_cleaned_data(request)
        ConfigService.set_by_category(self.category, data)
        return redirect(request.path)


class SiteInfoView(ConfigView):
    category = ConfigCategory.SITE
    template_name = 'config/site_info.html'
    extra_context = {
        'title': ConfigCategory.SITE.label,
    }

    def post(self, request, *args, **kwargs):
        data = self._get_cleaned_data(request)

        logo_file: UploadedFile = request.FILES.get('site_logo')
        if logo_file:
            service = UploadService()
            result = service.save(logo_file, FileType.IMAGE, request.user)

            data['site_logo'] = result.path

        ConfigService.set_by_category(self.category, data)
        return redirect(request.path)


class SystemSettingView(ConfigView):
    category = ConfigCategory.SYSTEM
    template_name = 'config/system_setting.html'
    extra_context = {
        'title': ConfigCategory.SYSTEM.label,
    }


class UploadSettingView(ConfigView):
    category = ConfigCategory.UPLOAD
    template_name = 'config/upload_setting.html'
    extra_context = {
        'title': ConfigCategory.UPLOAD.label,
        'path_rule': list(UploadPathRule),
    }

    def get(self, request, *args, **kwargs):
        config_data = ConfigService.get_by_category(self.category)

        upload_file_config = {}
        for key, ft in UPLOAD_FILE_CONFIG.items():
            upload_file_config[key] = ft.copy()
            upload_file_config[key]['size_value'] = config_data.get(ft['size_key'], ft['default_size'])
            upload_file_config[key]['type_value'] = config_data.get(ft['type_key'], ','.join(ft['default_type'])).split(',')

        self.extra_context['upload_file_config'] = upload_file_config
        return super().get(request)


class EmailConfigView(ConfigView):
    category = ConfigCategory.EMAIL
    template_name = 'config/email_settings.html'
    extra_context = {
        'title': ConfigCategory.EMAIL.label,
    }

    def get(self, request, *args, **kwargs):
        config_base = ConfigService.get_by_category(self.category)
        config_template = ConfigService.get_by_category(ConfigCategory.EMAIL_TEMPLATE)

        context = {
            'config_base': config_base,
            'config_template': config_template,
        }
        context.update(self.extra_context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        data.pop('csrfmiddlewaretoken', None)

        action = data.get('action', '')
        data.pop('action')
        match action:
            case 'reset':
                self._handle_reset()
            case 'email_base':
                self._handle_email_base(data)
            case 'email_template':
                self._handle_email_template(request.POST)
            case 'test':
                return self._handle_test(data)
            case 'test_template':
                return self._handle_test_template(data)
            case _:
                self.extra_context.update({'Error': _('Invalid action.')})

        return redirect(request.path)

    def _handle_reset(self):
        ConfigService.delete(category=self.category)

    def _handle_email_base(self, data):
        for key in ['email_use_ssl', 'email_use_tls']:
            data.setdefault(key, 'off')

        timeout = data.get('email_timeout')
        if timeout:
            data['email_timeout'] = timeout
        else:
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
            return api_response(1, gettext('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api_response(1, gettext('Invalid email address'))

        try:
            email = EmailService()
            res = email.send(to, subject, content)
            if res > 0:
                return api_response(0, gettext('Successfully sent email.'), {'has_send': res})
            else:
                return api_response(1, gettext('Failed to send email.'))
        except Exception as e:
            return api_response(1, gettext('Error while sending email: ') + str(e))

    @staticmethod
    def _handle_test_template(data):
        to = data.get('test_receiver', '').strip()
        raw_vars = data.get('test_variables', '').strip()

        if not to:
            return api_response(1, gettext('Recipient address is required.'))

        try:
            validate_email(to)
        except ValidationError:
            return api_response(1, gettext('Invalid email address'))

        try:
            variables = json.loads(raw_vars) if raw_vars else {}
        except JSONDecodeError:
            return api_response(1, gettext('Invalid JSON format for variables.'))

        try:
            email = EmailService()
            res = email.send_with_template(to, variables)
            if res > 0:
                return api_response(0, gettext('Successfully sent email.'), {'has_send': res})
            else:
                return api_response(1, gettext('Failed to send email.'))
        except Exception as e:
            return api_response(1, gettext('Error while sending email: ') + str(e))


class NavItemView(View):
    template_name = 'config/navitem_form.html'

    def get(self, request, *args, **kwargs):
        nav_id = kwargs.get('nav_id')
        nav_item_id = kwargs.get('nav_item_id', 0)

        nav = get_object_or_404(Nav, id=nav_id)
        nav_items = NavService.get_items(nav)

        if nav_item_id:
            nav_item = get_object_or_404(NavItem, id=nav_item_id, nav=nav)
            action = _('Edit')
        else:
            nav_item = NavItem(nav=nav)
            action = _('Add')

        context = {
            'title': f"{action} {_('Nav Item')}",
            'nav_id': nav_id,
            'nav_item_id': nav_item_id,
            'nav_item': nav_item,
            'nav_items': nav_items,
            'target': TargetChoices
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        nav_id = kwargs['nav_id']
        nav_item_id = kwargs.get('nav_item_id')

        # Get related objects (404 if not found)
        nav = get_object_or_404(Nav, id=nav_id)
        nav_item = get_object_or_404(NavItem, id=nav_item_id, nav=nav) if nav_item_id else None

        # Prepare POST data with enforced nav relationship
        post_data = request.POST.copy()
        post_data['nav'] = nav.id

        # Initialize form with bound data
        form = NavItemForm(post_data, nav_id=nav.id, instance=nav_item)
        if form.is_valid():
            form.save()
            if 'add_another' in request.POST:
                redirect_url = request.path
            else:
                redirect_url = reverse('admin:nav_items_edit', kwargs={'pk': nav_id})
            return redirect(redirect_url)

        return render(request, self.template_name, {
            'nav': nav,
            'nav_item': nav_item,
            'nav_id': nav_id,
            'nav_item_id': nav_item_id,
            'form': form,
            'target': TargetChoices
        })

    def delete(self, request, *args, **kwargs):
        """
        Delete a NavItem if it has no children.
        Returns 400 error if the node has child nodes to prevent accidental cascading deletes.
        """
        nav_item_id = kwargs.get('nav_item_id')
        try:
            nav_item = NavItem.objects.get(pk=nav_item_id)
        except NavItem.DoesNotExist:
            # Node not found, return 404 with translated error message
            return JsonResponse({'error': _('Node does not exist.')}, status=404)

        # Check if the node has children (replace 'children' with your related_name if different)
        if nav_item.children.exists():
            # Refuse deletion if children exist, with translated message
            return JsonResponse({
                'error': _('This node has child items and cannot be deleted. Please delete child items first.')
            }, status=400)

        # No children, safe to delete
        nav_item.delete()
        return JsonResponse({'message': _('Deleted successfully.')}, status=200)


class SpriteManagerView(View):
    template_name = 'config/sprite_manager.html'
    add_template_name = 'config/sprite_add.html'

    @staticmethod
    def _get_custom_sprite_file():
        """
        Get validated custom sprite file path with security checks
        """
        custom_sprite_path = getattr(settings, 'CUSTOM_SPRITE_FILE', CUSTOM_SPRITE_FILE)

        # Security check 1: Prevent path traversal
        if '..' in os.path.normpath(custom_sprite_path).split(os.sep):
            raise SuspiciousFileOperation("Relative paths are not allowed")
        if os.path.isabs(custom_sprite_path):
            raise SuspiciousFileOperation("Absolute paths are not allowed")

        # Security check 2: Ensure final path is within static dir
        static_dir = get_static_dir()
        full_path = os.path.abspath(os.path.join(static_dir, custom_sprite_path))
        if not os.path.commonpath([static_dir]) == os.path.commonpath([static_dir, full_path]):
            raise SuspiciousFileOperation(
                f"Invalid path traversal attempt: {full_path} not in {static_dir}"
            )

        return full_path

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        symbol_id = request.GET.get('symbol_id')
        if action == 'add':
            return render(request, self.add_template_name, {'title': 'Add Sprite Icon'})
        elif action == 'edit':
            context = {
                'title': 'Edit Sprite Icon',
                'symbol_id': symbol_id,
            }
            return render(request, self.add_template_name, context)

        # Find the path to the system sprite file
        sprite_file = finders.find('admin/svg/sprite.svg')
        # Get the custom sprite file path if it's configured
        custom_sprite_file = self._get_custom_sprite_file()

        icons, custom_icons = [], []

        # Load the built-in system sprite file and retrieve its symbol list
        try:
            manager = SpriteManager(sprite_file)
            icons = manager.list()
        except SpriteError:
            pass

        # If a custom sprite file is configured and exists, load its symbols as well
        if custom_sprite_file:
            try:
                custom_manager = SpriteManager(custom_sprite_file)
                custom_icons = custom_manager.list()
            except SpriteError:
                pass

        context = {
            'title': 'Sprite Manager',
            'icons': icons,
            'custom_icons': custom_icons,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        symbol_id = request.POST.get('symbol_id', '').strip()
        svg_code = request.POST.get('svg_code', '').strip()

        # Required fields validation
        if not symbol_id or not svg_code:
            context = {
                'symbol_id': symbol_id,
                'svg_code': svg_code,
                'message': _('Symbol ID and SVG code are required.')
            }
            return render(request, self.add_template_name, context)

        try:
            manager = SpriteManager(self._get_custom_sprite_file())

            # Add or update the icon in the sprite
            if manager.has(symbol_id):
                manager.update(symbol_id, svg_code)
            else:
                manager.add(symbol_id, svg_code)

            # On success → redirect to the sprite manager page
            return redirect(reverse('admin:icons_manage'))

        except Exception as e:
            # On error → stay on the current add page with error message
            context = {
                'symbol_id': symbol_id,
                'svg_code': svg_code,
                'message': _("Error: %(error)s") % {'error': e}
            }
            return render(request, self.add_template_name, context)

    def delete(self, request, *args, **kwargs):
        data = json.loads(request.body)
        symbol_id = data.get('symbol_id', '')

        if not symbol_id:
            return api_response(1, _('Symbol ID is required.'), status=400)

        try:
            manager = SpriteManager(self._get_custom_sprite_file())
            if manager.has(symbol_id):
                manager.remove(symbol_id)
                return api_response(0, _('Deleted successfully.'), status=200)
            else:
                return api_response(1, _('Symbol ID not found.'), status=404)
        except Exception as e:
            return api_response(1, _('Error: %(error)s') % {'error': e}, status=500)


class UploadFileView(View):
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        file_type_str = request.POST.get('file_type')

        if not uploaded_file or not file_type_str:
            return api_response(1, _('Missing file or file_type'), status=400)

        try:
            file_type = FileType(file_type_str)
        except ValueError:
            return api_response(1, _('Invalid file_type'), status=400)

        uploader = UploadService()
        info = uploader.save(uploaded_file, file_type, request.user)

        return api_response(0, _('Upload successful.'), info.to_dict())

    def delete(self, request, *args, **kwargs):
        file_path = request.GET.get("path")
        print(file_path)
        if not file_path:
            return api_response(1, _("Missing file path"), status=400)

        if UploadService.delete(file_path):
            return api_response(0, _("Delete successful."))
        return api_response(1, _("File not found"), status=404)


@staff_member_required
def sync_menu(request):
    result = AdminMenuManager.synchronize_menu(MenuSyncMode.SYNC_ALL, request.user)
    return render(request, 'config/sync_menu.html', {'result': result})


def nav_items_edit(request, pk):
    nav = Nav.objects.get(pk=pk)
    nav_items = NavService.get_items(nav)

    context = {
        'title': ConfigCategory.NAV.label,
        'nav': nav,
        'nav_items': nav_items,
    }
    return render(request, 'config/navigation.html', context)
