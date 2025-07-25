#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin module

Description:
  admin module of CMF
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cmfadmin import site, CMFModelAdmin
from cmfadmin.models import ExternalLink, Nav


class CmfUserAdmin(CMFModelAdmin, UserAdmin):
    add_form_template = "admin/auth/user/user_add.html"
    change_form_template = "admin/auth/user/user_change_form.html"

    def render_change_form(self, request, context, add=..., change=..., form_url=..., obj=..., ):
        admin_form = context.get("adminform")

        field_data = {}
        for i, fieldset in enumerate(admin_form):
            for field in fieldset:
                # Get the field name
                field_name = field.fields[0]

                # Get the field object
                field_object = field.form.fields.get(field_name)

                if field_object:
                    # Get all attributes and values of the field
                    field_properties = vars(field_object)
                    field_properties['name'] = field_name
                    # Get the initial value of the field
                    field_value = admin_form.form.initial.get(field_name, '')

                    # Handle special cases for many-to-many relationship fields
                    if field_name in {'user_permissions', 'groups'}:
                        # Convert the relationship queryset to a flat list of IDs
                        field_value = list(getattr(context['original'], field_name).values_list('id', flat=True))

                    # Add value to the field properties
                    field_properties['value'] = field_value

                    # Handle special _queryset field
                    if '_queryset' in field_properties:
                        queryset = field_properties['_queryset']
                        # Extract object information from _queryset
                        queryset_data = [{'id': obj.id, 'name': str(obj)} for obj in queryset]

                        # Store the _queryset data in the field properties dictionary
                        field_properties['queryset'] = queryset_data

                    # Store the field attributes and values in the dictionary
                    field_data[field_name] = field_properties

        context.update({'cmf': field_data})

        return super().render_change_form(request, context, add, change, form_url, obj)


class CmfGroupAdmin(CMFModelAdmin, GroupAdmin):
    add_form_template = "admin/auth/user/group_add.html"
    change_form_template = "admin/auth/user/group_add.html"


class ExternalLinksAdmin(CMFModelAdmin):
    list_display = ('sort_order', 'title', 'url_link', 'status')
    list_display_links = ('title',)
    list_editable = ('sort_order',)

    def url_link(self, obj):
        """Display the URL as a link that opens in a new tab in the list view"""
        if obj.url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)
        return "-"

    url_link.short_description = 'url'
    url_link.admin_order_field = 'url'


class NavAdmin(CMFModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'created_at', 'edit_nav')

    def edit_nav(self, obj):
        url = reverse('admin:nav_items_edit', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, _('Edit Menu'))

    edit_nav.short_description = _('Action')


# Unregister the default model registration in Django Admin
admin.site.unregister(User)
admin.site.unregister(Group)

# Register the model using the CrazyCMF admin class
site.register(User, CmfUserAdmin)
site.register(Group, CmfGroupAdmin)
site.register(ExternalLink, ExternalLinksAdmin)
site.register(Nav, NavAdmin)
