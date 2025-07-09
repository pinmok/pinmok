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

        # 限制parent只能选择同一导航下的项目
        if nav_id:
            self.fields['parent'].queryset = NavItem.objects.filter(nav_id=nav_id)

        # 编辑时排除自身作为父项
        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk=self.instance.pk)

        # 允许parent为空（表示顶级菜单）
        self.fields['parent'].required = False
        self.fields['parent'].widget.attrs['data-allow-null'] = 'true'
