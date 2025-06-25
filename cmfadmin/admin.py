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

from . import site, CMFModelAdmin


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


# 取消默认 admin 注册
admin.site.unregister(User)
admin.site.unregister(Group)

# 用你的自定义 admin 类注册
site.register(User, CmfUserAdmin)
site.register(Group, CmfGroupAdmin)
