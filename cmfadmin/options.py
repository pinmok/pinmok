#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
options module

Description:
  Custom base ModelAdmin for CMF admin site.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
from django.contrib.admin import ModelAdmin


class CMFModelAdmin(ModelAdmin):
    """
    Custom base ModelAdmin for CMF admin site.

    Reason:
    Django's default ModelAdmin hardcodes template paths for admin views
    (e.g. change_form_template, change_list_template). Even if custom templates
    with the same names exist in other template directories, Django will not
    use them unless these attributes are explicitly overridden.

    This class centralizes the template path definitions to ensure all admin
    views use custom templates, maintaining consistent admin interface styling
    and behavior across the entire CMF admin site.

    All admin classes must inherit from CMFModelAdmin to apply these overrides.
    """
    # add_form_template = "admin/add_form.html"
    change_form_template = "admin/change_form.html"
    change_list_template = "admin/change_list.html"
    delete_confirmation_template = "admin/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/delete_selected_confirmation.html"
    object_history_template = "admin/object_history.html"
    popup_response_template = "admin/popup_response.html"
