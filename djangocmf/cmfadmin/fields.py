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
from django.utils.translation import gettext_lazy as _

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
        empty_label = kwargs.get('empty_label', f'- {_("Select")} -')
        self.choices = [('', empty_label)] + [
            (node.id, mark_safe(label)) for node, label in pairs
        ]


class CMFImagePathField(forms.CharField):
    """
    A CharField that accepts image file paths produced by CMFImageFileInput
    in path mode. Replaces forms.ImageField to bypass file upload validation
    when the image is uploaded via AJAX and only the path is submitted.
    """
    pass
