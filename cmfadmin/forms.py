#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forms module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-04
"""
from django import forms

from cmfadmin.models import NavItem


class NavItemForm(forms.ModelForm):
    class Meta:
        model = NavItem
        fields = ['nav', 'parent', 'name', 'url', 'icon', 'target', 'sort_order', 'is_visible']

    def __init__(self, *args, **kwargs):
        nav_id = kwargs.pop('nav_id', None)  # 从kwargs中提取nav_id
        super().__init__(*args, **kwargs)

        # Limit the parent field to only select items under the same navigation
        if nav_id:
            self.fields['parent'].queryset = NavItem.objects.filter(nav_id=nav_id)

        # Exclude the current item from the list of possible parents when editing
        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk=self.instance.pk)

        # Allow parent to be null to represent a top-level menu item
        self.fields['parent'].required = False
        self.fields['parent'].widget.attrs['data-allow-null'] = 'true'
