#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forms module

Description:
  Custom forms for navigation items, users, and groups.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-04
"""
from django import forms

from djangocmf.cmfadmin.models import NavItem


class NavItemForm(forms.ModelForm):
    class Meta:
        model = NavItem
        fields = ['nav', 'parent', 'name', 'url', 'icon', 'target', 'sort_order', 'is_visible']

    def __init__(self, *args, **kwargs):
        nav_id = kwargs.pop('nav_id', None)
        super().__init__(*args, **kwargs)

        if nav_id:
            self.fields['parent'].queryset = NavItem.objects.filter(nav_id=nav_id)

        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk=self.instance.pk)

        self.fields['parent'].required = False
        self.fields['parent'].widget.attrs['data-allow-null'] = 'true'
