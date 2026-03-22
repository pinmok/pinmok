#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fields module

Description:
  Custom form fields for CMF admin.

  Provides reusable field classes that extend Django's built-in form fields
  to support CMF-specific UI patterns.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/3/22
"""
from django import forms
from django.utils.safestring import mark_safe

from djangocmf.core.libs.tree import T


class IndentedModelChoiceField(forms.ModelChoiceField):
    """
    A ModelChoiceField for tree-structured FK fields.

    Choices are ordered and indented according to DFS pre-order from
    ``TreeNode.flatten_with_indent()``, while the queryset is retained
    solely for FK validation and assignment.

    Args:
        pairs: Output of ``TreeNode.flatten_with_indent()``.
    """

    def __init__(self, pairs: list[tuple[T, str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        empty_label = kwargs.get('empty_label', '---------')
        self.choices = [('', empty_label)] + [
            (node.id, mark_safe(label)) for node, label in pairs
        ]
