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
import json

from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from djangocmf import cmfadmin
from djangocmf.cmfadmin.models import ExternalLink, Nav
from djangocmf.cmfadmin.options import CMFModelAdmin
from djangocmf.cmfadmin.service.authorization import PermissionService


class CmfUserAdmin(UserAdmin, CMFModelAdmin):
    """
    Custom admin for Django's User model with CMF enhancements.

    Note: This is registered in apps.py, not here.
    """
    add_form_template = "admin/auth/user/user_add.html"
    change_form_template = "admin/auth/user/user_change_form.html"

    def render_change_form(self, request, context, add=..., change=..., form_url=..., obj=..., ):
        """
       Render the change/add form with dynamic field metadata.
       """
        # Attach permission tree if applicable
        perms_tree = PermissionService.get_permission_tree_for_instance(obj)
        permissions = json.dumps([node.to_dict() for node in perms_tree])

        context.update({'permissions': permissions, 'model_type': 'user'})

        return super().render_change_form(request, context, add, change, form_url, obj)

    def save_model(self, request, obj, form, change):
        """
        Save extra permissions for the user.

        - Basic user fields are automatically handled by Admin.
        - Only custom logic (menu permissions, business permissions) is needed here.
        """
        super().save_model(request, obj, form, change)
        # Save menu permissions
        PermissionService.save_menu_permissions(obj, request.POST.getlist("menu_permissions[]"))
        # Save custom permissions
        PermissionService.save_custom_permissions(obj, request.POST.getlist("custom_permissions[]"))


class CmfGroupAdmin(GroupAdmin, CMFModelAdmin):
    """
    Custom admin for Django's Group model with CMF enhancements.

    Note: This is registered in apps.py, not here.
    """
    add_form_template = "admin/auth/user/group_add.html"
    change_form_template = "admin/auth/user/group_add.html"

    def render_change_form(self, request, context, add=..., change=..., form_url=..., obj=..., ):
        perms_tree = PermissionService.get_permission_tree_for_instance(obj)
        permissions = json.dumps([node.to_dict() for node in perms_tree])

        context.update({'permissions': permissions, 'model_type': 'group'})
        return super().render_change_form(request, context, add, change, form_url, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Save menu permissions
        PermissionService.save_menu_permissions(obj, request.POST.getlist("menu_permissions[]"))
        # Save custom permissions
        PermissionService.save_custom_permissions(obj, request.POST.getlist("custom_permissions[]"))


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
