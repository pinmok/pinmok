#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_forms

Description:
  Provides ConfigForm — a dynamic form that builds its fields from CONFIG_SCHEMA.
  Each ConfigType maps to a specific Django form field and CMF widget.

  Intended usage:
    - Subclass ConfigForm and set `category` to bind it to a schema category.
    - Use `fieldsets` in the ModelAdmin subclass to control layout, exactly as
      with standard Django ModelAdmin.
    - On save, call form.save() which delegates to ConfigService.set_many().

  Example::

    class SiteConfigForm(ConfigForm):
        category = ConfigCategory.SITE

    class SiteConfigAdmin(CMFModelAdmin):
        form = SiteConfigForm
        fieldsets = [
            (_("Basic"), {"fields": ["site_name", "site_slogan", "site_logo"]}),
        ]

Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""
import copy
import json
from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin import widgets
from djangocmf.cmfadmin.config_schema import CONFIG_SCHEMA
from djangocmf.cmfadmin.enums import ConfigType, ConfigCategory, UploadConfigKey
from djangocmf.cmfadmin.service.config import ConfigService
from djangocmf.cmfadmin.widgets import CMFCheckboxSelectMultiple

# ---------------------------------------------------------------------------
# ConfigType → (field_class, widget_class) mapping
# Entries without a widget (None) use the field's default widget.
# ---------------------------------------------------------------------------
_FIELD_MAP: dict[ConfigType, tuple[type[forms.Field], type[forms.Widget] | None]] = {
    ConfigType.STR: (forms.CharField, widgets.CMFTextInput),
    ConfigType.TEXT: (forms.CharField, widgets.CMFTextarea),
    ConfigType.INT: (forms.IntegerField, widgets.CMFNumberInput),
    ConfigType.FLOAT: (forms.FloatField, widgets.CMFNumberInput),
    ConfigType.BOOL: (forms.BooleanField, widgets.CMFCheckbox),
    ConfigType.JSON: (forms.CharField, widgets.CMFTextarea),
    ConfigType.DATETIME: (forms.DateTimeField, widgets.CMFDateTimeInput),
    ConfigType.IP: (forms.GenericIPAddressField, widgets.CMFGenericIPAddress),
    ConfigType.URL: (forms.URLField, widgets.CMFURLInput),
    ConfigType.EMAIL: (forms.EmailField, widgets.CMFEmailInput),
    ConfigType.IMAGE: (forms.CharField, widgets.CMFImageFileInput),
    ConfigType.FILE: (forms.FileField, widgets.CMFFileInput),
    ConfigType.MULTI_SELECT: (forms.MultipleChoiceField, widgets.CMFSelectTags),
}


def _build_field(key: str, field_schema: dict) -> forms.Field:
    """
    Build a single form field from a schema entry.

    Handles:
      - Required flag (defaults to False for config fields)
      - Choices (renders Select or MultipleChoiceField)
      - help_text and label from schema
      - Correct widget instantiation per ConfigType
    """
    cfg_type: ConfigType = field_schema.get("type", ConfigType.STR)
    label = field_schema.get("label", key)
    help_text = field_schema.get("help_text", "")
    required = field_schema.get("required", False)
    choices: list | None = field_schema.get("choices")

    field_class, widget_class = _FIELD_MAP.get(cfg_type, (forms.CharField, widgets.CMFTextInput))

    # --- widget ---
    widget = field_schema.get("widget")
    if widget is None:
        if choices and cfg_type == ConfigType.MULTI_SELECT:
            widget = widget_class()
        elif choices:
            # Single-select: use CMFSelect
            widget = widgets.CMFSelect()
        elif widget_class is not None:
            widget = widget_class()
        else:
            widget = None

    # --- field kwargs ---
    kwargs: dict[str, Any] = {
        "label": label,
        "required": required,
        "help_text": help_text,
    }
    if widget is not None:
        kwargs["widget"] = widget

    # --- choices ---
    if choices:
        field_class = forms.MultipleChoiceField if cfg_type == ConfigType.MULTI_SELECT else forms.ChoiceField
        if cfg_type == ConfigType.MULTI_SELECT:
            kwargs["choices"] = list(choices)
        else:
            # Prepend empty option for non-required single-select fields.
            if not required:
                kwargs["choices"] = [("", _("— select —"))] + list(choices)
            else:
                kwargs["choices"] = list(choices)

    # --- type-specific overrides ---
    if cfg_type == ConfigType.BOOL:
        # BooleanField is always optional in config context.
        kwargs["required"] = False

    if cfg_type in (ConfigType.IMAGE, ConfigType.FILE):
        # File fields are never required on edit forms (existing value is kept).
        kwargs["required"] = False

    if cfg_type == ConfigType.JSON:
        # Validate JSON on the field level.
        kwargs.setdefault("validators", [])

    return field_class(**kwargs)


class ImproperlyConfiguredError(Exception):
    pass


class ConfigForm(forms.Form):
    """
    Dynamic config form.  Subclasses must define `category`.

    Fields are built from CONFIG_SCHEMA at class creation time via the
    metaclass, so they behave exactly like handwritten form fields —
    fieldsets, field ordering, and widget rendering all work normally.

    Subclass example::
        class SiteConfigForm(ConfigForm):
            category = ConfigCategory.SITE

    The `initial` data is loaded automatically from ConfigService when the
    form is instantiated without data (i.e. GET request).  On POST, pass
    `request.POST` and `request.FILES` as usual.

    Calling `save()` persists all cleaned values via ConfigService.set_many().
    """

    category: str | None = None  # Subclasses must set this

    def __init__(self, data=None, files=None, **kwargs):
        if self.category is None:
            raise ImproperlyConfiguredError(
                f"{self.__class__.__name__} must define 'category'."
            )

        # Load initial values from ConfigService when not processing a POST.
        if data is None and "initial" not in kwargs:
            kwargs["initial"] = ConfigService.get_category_raw(self.category)

        super().__init__(data=data, files=files, **kwargs)

        # Deep-copy all fields so each form instance has independent field/widget objects.
        # This prevents widget state from leaking between instances when fields are
        # defined at class level (as in __init_subclass__).
        self.fields = {
            key: copy.deepcopy(field)
            for key, field in self.fields.items()
        }

    def __init_subclass__(cls, **kwargs):
        """
        Build form fields from CONFIG_SCHEMA when a subclass is defined.
        Fields are injected into the class so they appear in cls.declared_fields,
        which is what Django's Form metaclass uses for field ordering and access.
        """
        super().__init_subclass__(**kwargs)
        category = getattr(cls, "category", None)
        if category is None:
            return

        schema = CONFIG_SCHEMA.get(category, {})
        for key, field_schema in schema.items():
            # Only add if not already explicitly defined on the subclass.
            if key not in cls.__dict__:
                cls.declared_fields = getattr(cls, "declared_fields", {}).copy()
                cls.declared_fields[key] = _build_field(key, field_schema)
                setattr(cls, key, cls.declared_fields[key])

    def clean(self):
        cleaned = super().clean()

        schema = CONFIG_SCHEMA.get(self.category, {})
        for key, value in list(cleaned.items()):
            field_schema = schema.get(key, {})
            cfg_type = field_schema.get("type", ConfigType.STR)

            # JSON fields: validate and normalise to compact string.
            if cfg_type == ConfigType.JSON and value:
                try:
                    parsed = json.loads(value)
                    cleaned[key] = json.dumps(parsed, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    self.add_error(key, _("Enter valid JSON."))

            # BOOL: unchecked checkbox comes through as False, that's fine.
            # MULTI_SELECT: value is already a list from MultipleChoiceField.

        return cleaned

    def save(self) -> None:
        """
        Persist all cleaned values via ConfigService.

        File fields (IMAGE, FILE) are skipped if no new file was uploaded
        (i.e. the cleaned value is None/empty), preserving the existing value.
        """
        if not self.is_valid():
            raise ValueError("Cannot save an invalid form.")

        schema = CONFIG_SCHEMA.get(self.category, {})
        data_to_save: dict[str, Any] = {}

        for key, value in self.cleaned_data.items():
            field_schema = schema.get(key, {})
            cfg_type = field_schema.get("type", ConfigType.STR)

            # Skip file fields with no new upload.
            if cfg_type in (ConfigType.IMAGE, ConfigType.FILE) and not value:
                continue

            data_to_save[key] = value
            
        assert self.category is not None
        ConfigService.set_many(self.category, data_to_save)


class EmailConfigForm(ConfigForm):
    """
    Email configuration form with mutual exclusivity validation for SSL and TLS.

    Extends ConfigForm to add a clean() check that prevents smtp_use_ssl and
    smtp_use_tls from being enabled simultaneously, which is an invalid
    combination in Django's email backend.
    """
    category = ConfigCategory.EMAIL

    def clean(self):
        cleaned_data = super().clean()
        use_tls = cleaned_data.get("smtp_use_tls")
        use_ssl = cleaned_data.get("smtp_use_ssl")
        if use_tls and use_ssl:
            raise forms.ValidationError(_("TLS and SSL cannot be enabled at the same time."))
        return cleaned_data


class UploadConfigForm(ConfigForm):
    category = ConfigCategory.UPLOAD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in [
            UploadConfigKey.IMAGE_TYPE,
            UploadConfigKey.AUDIO_TYPE,
            UploadConfigKey.VIDEO_TYPE,
            UploadConfigKey.DOCUMENT_TYPE,
            UploadConfigKey.ARCHIVE_TYPE,
        ]:
            self.fields[key].widget = CMFCheckboxSelectMultiple(
                choices=self.fields[key].widget.choices
            )
