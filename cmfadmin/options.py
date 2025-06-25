#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
options module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
from django.contrib.admin import ModelAdmin


class CMFModelAdmin(ModelAdmin):
    add_form_template = "admin/add_form.html"
    change_form_template = "admin/change_form.html"
    change_list_template = "admin/change_list.html"
    delete_confirmation_template = "admin/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/delete_selected_confirmation.html"
    object_history_template = "admin/object_history.html"
    popup_response_template = "admin/popup_response.html"
