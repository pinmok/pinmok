#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
widgets module

Description:
  Provides custom Django form widgets with Tabler styling.
  Centralizes UI-related widget customization to ensure consistent backend form appearance.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/2/1
"""
from django import forms
from django.conf import settings
from django.contrib.admin.widgets import (
    AdminUUIDInputWidget, AdminRadioSelect, ForeignKeyRawIdWidget, AdminFileWidget,
    AutocompleteMixin, ManyToManyRawIdWidget, AdminURLFieldWidget, )


class CMFWidgetMixin:
    """
    Base mixin for all CMF Widgets.

    Subclasses must define default_css_class.
    This mixin does not provide any inference logic.

    Mixin must be used with a Widget subclass.
    """
    default_css_class = 'form-control'  # must be set by subclass
    icon_name = None

    def __init__(self, *args, attrs=None, **kwargs):
        # Set default class; user-provided attrs will override defaults
        attrs = {'class': self.default_css_class, **(attrs or {})}
        # User attrs override default class
        super().__init__(*args, attrs=attrs, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.icon_name:
            context['widget']['icon_name'] = self.icon_name
        return context


# Text input series
class CMFTextInput(CMFWidgetMixin, forms.TextInput):
    pass


class CMFEmailInput(CMFWidgetMixin, forms.EmailInput):
    pass


class CMFURLInput(CMFWidgetMixin, AdminURLFieldWidget):  # forms.URLInput):
    pass


class CMFNumberInput(CMFWidgetMixin, forms.NumberInput):
    pass


class CMFUUIDInput(CMFWidgetMixin, AdminUUIDInputWidget):
    pass


class CMFDecimalInput(CMFWidgetMixin, forms.NumberInput):
    def __init__(self, attrs=None):
        attrs = {'placeholder': '0.00', **(attrs or {})}
        # User attrs override default class
        super().__init__(attrs=attrs)


class CMFGenericIPAddress(CMFWidgetMixin, forms.TextInput):
    def __init__(self, attrs=None):
        attrs = {
            'data-mask': '0[0][0].0[0][0].0[0][0].0[0][0]',
            'placeholder': '000.000.000.000',
            'autocomplete': 'on',
            **(attrs or {})
        }
        # User attrs override default class
        super().__init__(attrs=attrs)

    class Media:
        js = ('admin/js/imask.min.js',)


# Textarea
class CMFTextarea(CMFWidgetMixin, forms.Textarea):
    pass


# Select
class CMFSelect(CMFWidgetMixin, forms.Select):
    default_css_class = 'form-select'


class CMFSelectMultiple(CMFWidgetMixin, forms.SelectMultiple):
    default_css_class = 'form-select'


# Checkbox / Radio
class CMFCheckboxInput(CMFWidgetMixin, forms.CheckboxInput):
    default_css_class = 'form-check-input'


class CMFRadioSelect(CMFWidgetMixin, AdminRadioSelect):
    default_css_class = 'form-check-input'
    option_template_name = 'forms/widgets/input_option.html'


class CMFForeignKeyRawId(CMFWidgetMixin, ForeignKeyRawIdWidget):
    pass


class CMFManyToManyRawId(CMFWidgetMixin, ManyToManyRawIdWidget):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.admin_site.is_registered(self.rel.model):
            # The related object is registered with the same AdminSite
            context["widget"]["attrs"]["class"] = f"{self.default_css_class} vManyToManyRawIdAdminField".strip()
        return context


class CMFAutocompleteMixin(AutocompleteMixin):
    def __init__(self, field, admin_site, attrs=None, choices=(), using=None):
        attrs = {"class": "form-select", **(attrs or {})}
        super().__init__(field, admin_site, attrs, choices, using)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)

        # Remove the attributes specified for select2
        select2_specific = [
            'data-ajax--cache', 'data-ajax--delay', 'data-ajax--type', 'data-theme',
        ]
        for attr in select2_specific:
            attrs.pop(attr, None)

        return attrs

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return forms.Media(
            js=(
                "admin/js/vendor/jquery/jquery%s.js" % extra,
                "libs/tom-select/js/tom-select.complete%s.js" % extra,
                "admin/js/autocomplete.js",
            ),
            css={
                "screen": (
                    "libs/tom-select/css/tom-select.tabler%s.css" % extra,
                ),
            },
        )


class CMFAutocompleteSelect(CMFAutocompleteMixin, forms.Select):
    pass


class CMFAutocompleteSelectMultiple(CMFAutocompleteMixin, forms.SelectMultiple):
    pass


class CMFFileInput(CMFWidgetMixin, AdminFileWidget):
    template_name = "admin/widgets/clearable_file_input.html"
    default_css_class = 'form-control'


class CMFImageFileInput(CMFFileInput):
    # TODO 添加裁切
    pass


class BaseCMFDateTimeMixin(CMFWidgetMixin):
    template_name = "admin/widgets/datetime.html"

    def __init__(self, attrs=None, format=None):  # noqa
        # Handle style merging: user styles are appended, not overridden
        attributes = attrs or {}
        style = attributes.pop("style", '')
        merged_style = f'{style} max-width: 12rem;'.strip()
        attrs = {'style': merged_style, **attributes}
        super().__init__(attrs=attrs, format=format)


class CMFDateInput(BaseCMFDateTimeMixin, forms.DateInput):
    input_type = 'date'
    icon_name = 'tabler-calendar'


class CMFTimeInput(BaseCMFDateTimeMixin, forms.TimeInput):
    input_type = 'time'
    icon_name = 'tabler-clock-hour'


class CMFDateTimeInput(BaseCMFDateTimeMixin, forms.DateTimeInput):
    input_type = 'datetime-local'
    icon_name = 'tabler-calendar-time'
