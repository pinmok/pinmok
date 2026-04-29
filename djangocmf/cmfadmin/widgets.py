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
import json

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import (
    AdminUUIDInputWidget, AdminRadioSelect, ForeignKeyRawIdWidget, AdminFileWidget,
    AutocompleteMixin, ManyToManyRawIdWidget, AdminURLFieldWidget, )
from django.core.files.storage import default_storage
from django.forms import Widget
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import get_language

from djangocmf.cmfadmin.constants import HUGERTE_LANG_MAP
from djangocmf.cmfadmin.enums import ImageWidgetMode


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
        """ Provide icons name for input fields that include built-in icons. """
        context = super().get_context(name, value, attrs)  # type: ignore
        if self.icon_name:
            context['widget']['icon_name'] = self.icon_name
        return context


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


class CMFTextarea(CMFWidgetMixin, forms.Textarea):
    def __init__(self):
        super().__init__(attrs={"rows": "3"})


class CMFPassword(CMFWidgetMixin, forms.PasswordInput):
    pass


class CMFSelect(CMFWidgetMixin, forms.Select):
    default_css_class = 'form-select'


class CMFSelectMultiple(CMFWidgetMixin, forms.SelectMultiple):
    default_css_class = 'form-select'


class CMFSelectTags(forms.SelectMultiple):
    def __init__(self, *args, attrs=None, **kwargs):
        # Set default class; user-provided attrs will override defaults
        attrs = {'class': 'form-select', **(attrs or {})}
        user_class = attrs.get('class')
        attrs['class'] = f'{user_class} select-multiple-tags'.strip()

        # User attrs override default class
        super().__init__(*args, attrs=attrs, **kwargs)

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return forms.Media(
            js=(
                "admin/js/vendor/jquery/jquery%s.js" % extra,
                "libs/tom-select/js/tom-select.complete%s.js" % extra,
                "admin/js/widgets/select_tags_input.js",
            ),
            css={
                "screen": (
                    "libs/tom-select/css/tom-select.tabler%s.css" % extra,
                ),
            },
        )


# Checkbox / Radio
class CMFCheckbox(CMFWidgetMixin, forms.CheckboxInput):
    default_css_class = 'form-check-input'


class CMFCheckboxSelectMultiple(CMFWidgetMixin, forms.CheckboxSelectMultiple):
    default_css_class = 'form-selectgroup-input'
    template_name = 'forms/widgets/checkbox_select_multiple.html'
    option_template_name = 'forms/widgets/checkbox_select_multiple_option.html'


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


class CMFImageFileInput(Widget):
    """
    Image upload widget with built-in cropper support.

    Renders a preview image, a hidden input for the file path,
    and a trigger button that opens the cropper modal.

    The cropper modal is injected into the DOM by the widget's JS.
    The file is uploaded on form submit, not when the user finishes cropping.

    Attributes passed via attrs:
        data-crop          : 'true' | 'false' — enable/disable cropper (default: true)
        data-aspect-ratio  : e.g. '16:9', '1:1', '1.5' — fixed crop ratio (default: free)
        data-target-width  : max output width in pixels (default: 1920)
        data-target-height : max output height in pixels (default: none)
    """
    template_name = "admin/widgets/image_cropper.html"
    needs_multipart_form = True

    class Media:
        css = {
            'all': ('libs/cropperjs/cropper.min.css',)
        }
        js = (
            'libs/cropperjs/cropper.min.js',
            'admin/js/widgets/cropper.js',
        )

    def __init__(self, attrs=None, mode: str = ImageWidgetMode.PATH):
        # mode: 'path' for ImageField, 'resource' for ForeignKey(Resource)
        if mode not in ImageWidgetMode:
            raise ValueError("mode must be 'path' or 'resource'")
        self.mode = mode
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        final_attrs = context['widget']['attrs']
        context['widget']['crop'] = final_attrs.get('crop', 'true')
        context['widget']['aspect_ratio'] = final_attrs.get('aspectRatio', '')
        context['widget']['target_width'] = final_attrs.get('targetWidth', '1900')
        context['widget']['target_height'] = final_attrs.get('targetHeight', '')
        context['widget']['mode'] = self.mode
        lock_ratio_raw = final_attrs.get('lockRatio', 'false')
        context['widget']['lock_ratio'] = 'true' if lock_ratio_raw == 'true' else 'false'

        # Upload URL — resolved at render time
        context['widget']['upload_url'] = reverse('admin:cmfadmin:upload_file')

        # Placeholder shown when no image is set
        context['widget']['placeholder'] = static('admin/svg/photo-up.svg')

        # Resolve preview URL depending on mode
        preview_url = None
        if self.mode == 'resource':
            # value is a Resource pk (int or string digit)
            if value and str(value).isdigit():
                from djangocmf.cmfadmin.models import Resource
                try:
                    resource = Resource.objects.get(pk=int(value))
                    preview_url = default_storage.url(resource.url)
                except Resource.DoesNotExist:
                    pass
        else:
            # Original 'path' mode
            if value and hasattr(value, 'url'):
                preview_url = value.url
            elif value and isinstance(value, str) and value:
                preview_url = default_storage.url(value)

        context['widget']['preview_url'] = preview_url
        return context


class BaseCMFDateTimeMixin(CMFWidgetMixin):
    template_name = "admin/widgets/datetime.html"

    def __init__(self, attrs=None, format=None):  # noqa A003
        # Handle style merging: user styles are appended, not overridden
        attributes = attrs or {}
        style = attributes.pop("style", '')
        merged_style = f'{style} max-width: 13rem;'.strip()
        attrs = {'style': merged_style, **attributes}

        if format is None:
            format = getattr(self, 'format', None)  # noqa A003

        super().__init__(attrs=attrs, format=format)


class CMFDateInput(BaseCMFDateTimeMixin, forms.DateInput):
    input_type = 'date'
    icon_name = 'tabler-calendar'
    format = '%Y-%m-%d'


class CMFTimeInput(BaseCMFDateTimeMixin, forms.TimeInput):
    input_type = 'time'
    icon_name = 'tabler-clock-hour'
    format = '%H:%M'


class CMFDateTimeInput(BaseCMFDateTimeMixin, forms.DateTimeInput):
    input_type = 'datetime-local'
    icon_name = 'tabler-calendar-time'
    format = '%Y-%m-%dT%H:%M'


class HugeRTEWidget(forms.Textarea):
    """
    Textarea widget that initializes the HugeRTE rich-text editor.
    Config is serialized to a data attribute and picked up by hugerte.js.
    """
    BASE_CONFIG = {
        'branding': False,
        'menubar': False,
        'plugins': [
            'advlist', 'anchor', 'lists', 'link', 'image', 'table', 'code', 'fullscreen', 'preview',
            'searchreplace', 'autoresize', 'wordcount', 'help', 'media'
        ],
        'toolbar': (
            'code|undo redo|styles|bold italic underline strikethrough|forecolor backcolor|'
            'subscript superscript|alignleft aligncenter alignright alignjustify|'
            'anchor removeformat|bullist numlist|outdent indent|link image media table|fullscreen preview help'
        ),
        'toolbar_mode': 'wrap',
        'min_height': 300,
    }

    def __init__(self, extra_config=None, attrs=None):
        # extra_config: user-supplied options that override BASE_CONFIG
        self.extra_config = extra_config or {}
        super().__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        config = {**self.BASE_CONFIG}

        # Convert Django language code to HugeRTE RFC 5646 language value
        lang_code = get_language()
        hugerte_lang = None if lang_code is None else HUGERTE_LANG_MAP.get(lang_code.lower())
        if hugerte_lang:
            config['language'] = hugerte_lang

        # User-supplied config overrides BASE_CONFIG
        config.update(self.extra_config)

        final_attrs = self.build_attrs(self.attrs or {}, attrs or {})
        existing_class = final_attrs.get('class', '')
        final_attrs['class'] = (existing_class + ' hugerte-editor').strip()
        final_attrs['data-hugerte-config'] = json.dumps(config, ensure_ascii=False)

        return super().render(name, value, attrs=final_attrs, renderer=renderer)

    class Media:
        js = (
            'libs/hugerte/hugerte.min.js',
            'admin/js/widgets/hugerte.js',
        )


class ResourceWidget(CMFForeignKeyRawId):
    """
    Enhanced raw-id widget for ForeignKey(Resource) fields.

    Inherits all standard behaviour from ForeignKeyRawIdWidget:
    - The magnifier button opens the resource selector popup
    - The add button opens the resource upload popup (add_view)
    - Popup callback and value writing are handled by Django's admin JS

    Visual enhancements added by this widget:
    - The raw ID input is hidden (still present in DOM for Django's JS)
    - Selected resource is shown as thumbnail (image) or filename (other types)
    - A clear button sets the hidden input to empty
    """
    template_name = "admin/widgets/resource_foreign_key_raw_id.html"

    class Media:
        js = ('admin/js/widgets/resource_widget.js',)


class CMFDatalistInput(CMFWidgetMixin, forms.TextInput):
    """
    Text input with a datalist dropdown for suggesting existing values.
    Accepts any iterable via the options parameter; the caller is responsible
    for providing the data source.
    """
    default_css_class = 'form-control'
    template_name = 'forms/widgets/datalist_input.html'

    def __init__(self, options=(), attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.options = options

    def get_context(self, name, value, attrs):
        attributes = {'list': f'{name}_list', **(attrs or {})}
        context = super().get_context(name, value, attributes)
        context['widget']['datalist_id'] = f'{name}_list'
        context['widget']['options'] = self.options
        return context
