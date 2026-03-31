#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
options module

Description:

Author:
  惠达浪 <crazys@126.com>
Created:
  2026/2/1
"""
from dataclasses import dataclass

from django import forms
from django.contrib import messages
from django.contrib.admin.options import get_ul_class, BaseModelAdmin, ModelAdmin, TabularInline, StackedInline
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin import widgets
from djangocmf.cmfadmin.enums import ImageWidgetMode
from djangocmf.cmfadmin.fields import CMFImagePathField
from djangocmf.core.constants import DEFAULT_SORT_ORDER


class CMFModelAdminMixin(BaseModelAdmin):
    """
    CMF default ModelAdmin mixin.

    Automatically applies Tabler-style widgets while retaining
    all Django customization points.
    """
    formfield_overrides = {
        models.DateTimeField: {
            "form_class": forms.DateTimeField,
            "widget": widgets.CMFDateTimeInput,
        },
        models.DateField: {"widget": widgets.CMFDateInput},
        models.TimeField: {"widget": widgets.CMFTimeInput},
        models.TextField: {"widget": widgets.CMFTextarea},
        models.URLField: {"widget": widgets.CMFURLInput},
        models.IntegerField: {"widget": widgets.CMFNumberInput},
        models.BigIntegerField: {"widget": widgets.CMFNumberInput},
        models.DecimalField: {"widget": widgets.CMFDecimalInput},
        models.FloatField: {"widget": widgets.CMFNumberInput},
        models.CharField: {"widget": widgets.CMFTextInput},
        models.ImageField: {"widget": widgets.CMFFileInput},
        models.FileField: {"widget": widgets.CMFFileInput},
        models.EmailField: {"widget": widgets.CMFEmailInput},
        models.UUIDField: {"widget": widgets.CMFUUIDInput},
        models.BooleanField: {"widget": widgets.CMFCheckbox},
        models.GenericIPAddressField: {"widget": widgets.CMFGenericIPAddress},
        models.JSONField: {'widget': widgets.CMFTextarea},
    }

    # Controls the sort position of this model in the admin menu.
    # Lower values appear first. Defaults to DEFAULT_SORT_ORDER (10000).
    menu_order: int = DEFAULT_SORT_ORDER
    image_crop_fields: list = []

    @property
    def action_form(self):
        """
        Originally a class attribute, converted to a property to avoid
        AppRegistryNotReady error caused by early import of CMFActionForm,
        which transitively imports models before Django's app registry is ready.
        """
        from djangocmf.cmfadmin.forms.forms import CMFActionForm
        return CMFActionForm

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """
        Get a form Field for a database Field that has declared choices.
        """
        # Avoid stomping on custom widget/choices arguments.
        if "widget" not in kwargs:
            if db_field.name in self.radio_fields:
                kwargs["widget"] = widgets.CMFRadioSelect(
                    attrs={
                        "class": get_ul_class(self.radio_fields[db_field.name]),
                    }
                )
            else:
                kwargs["widget"] = widgets.CMFSelect()

        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Get a form Field for a ForeignKey.
        ForeignKey fields pointing to Resource are automatically rendered
        with CMFForeignKeyRawId widget, requiring no configuration from the developer.
        """
        db = kwargs.get("using")

        # Auto-apply raw_id widget for all Resource FK fields.
        # This takes precedence over all other widget configurations.
        from djangocmf.cmfadmin.models import Resource  # avoid circular import
        if db_field.related_model is Resource and "widget" not in kwargs:
            kwargs["widget"] = widgets.ResourceWidget(
                db_field.remote_field, self.admin_site, using=db
            )
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if "widget" not in kwargs:
            if db_field.name in self.get_autocomplete_fields(request):
                kwargs["widget"] = widgets.CMFAutocompleteSelect(
                    db_field, self.admin_site, using=db
                )
            elif db_field.name in self.raw_id_fields:
                kwargs["widget"] = widgets.CMFForeignKeyRawId(
                    db_field.remote_field, self.admin_site, using=db
                )
            elif db_field.name in self.radio_fields:
                kwargs["widget"] = widgets.CMFRadioSelect(
                    attrs={
                        "class": get_ul_class(self.radio_fields[db_field.name]),
                    }
                )
                kwargs["empty_label"] = (
                    kwargs.get("empty_label", _("None")) if db_field.blank else None
                )
            else:
                kwargs["widget"] = widgets.CMFSelect()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Get a form Field for a ManyToManyField.
        """
        # If it uses an intermediary model that isn't auto created, don't show
        # a field in admin.
        if not db_field.remote_field.through._meta.auto_created:
            return None
        db = kwargs.get("using")

        if "widget" not in kwargs:
            autocomplete_fields = self.get_autocomplete_fields(request)
            if db_field.name in autocomplete_fields:
                kwargs["widget"] = widgets.CMFAutocompleteSelectMultiple(
                    db_field,
                    self.admin_site,
                    using=db,
                )
            elif db_field.name in self.raw_id_fields:
                kwargs["widget"] = widgets.CMFManyToManyRawId(
                    db_field.remote_field,
                    self.admin_site,
                    using=db,
                )
            elif db_field.name in [*self.filter_vertical, *self.filter_horizontal]:
                kwargs["widget"] = FilteredSelectMultiple(
                    db_field.verbose_name, db_field.name in self.filter_vertical
                )
            else:
                kwargs["widget"] = widgets.CMFSelectMultiple()

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def _apply_crop_fields(self, base_fields):
        """
        Replace widget (and form field where necessary) for fields listed in
        image_crop_fields.

        Accepts list (no config) or dict (with per-field config).

        Dict values may contain:
            mode        : 'path' (default) or 'resource'
            data-*      : HTML attrs forwarded to the widget

        In path mode, if the original form field is forms.ImageField, it is
        replaced with CMFImagePathField so that a string path passes validation.
        In resource mode, the form field is left unchanged (ModelChoiceField
        handles string PKs natively).
        """
        if isinstance(self.image_crop_fields, dict):
            items = self.image_crop_fields.items()
        else:
            items = ((field_name, {}) for field_name in self.image_crop_fields)

        for field_name, config in items:
            if field_name not in base_fields:
                continue

            # Separate mode from HTML attrs
            mode = config.get('mode', ImageWidgetMode.PATH)
            extra_attrs = {k: v for k, v in config.items() if k != 'mode'}

            form_field = base_fields[field_name]
            existing_attrs = getattr(form_field.widget, 'attrs', {})
            merged_attrs = {**existing_attrs, **extra_attrs}

            form_field.widget = widgets.CMFImageFileInput(attrs=merged_attrs, mode=mode)

            # In path mode, forms.ImageField rejects string paths — replace it
            if mode == ImageWidgetMode.PATH and isinstance(form_field, forms.ImageField):
                base_fields[field_name] = CMFImagePathField(
                    required=form_field.required,
                    label=form_field.label,
                    help_text=form_field.help_text,
                    widget=form_field.widget,
                )


class CMFModelAdmin(CMFModelAdminMixin, ModelAdmin):
    back_url = None

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if self.back_url:
            extra_context['back_url'] = self.back_url
        return super().changeform_view(request, object_id, form_url, extra_context)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Remove related widget action buttons and set parent choices with tree indentation."""
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if (
                formfield
                and hasattr(db_field, 'related_model')
                and db_field.related_model == db_field.model
                and hasattr(formfield.widget, 'can_add_related')
        ):
            formfield.widget.can_add_related = False
            formfield.widget.can_change_related = False
            formfield.widget.can_delete_related = False
            formfield.widget.can_view_related = False
        return formfield

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        self._apply_crop_fields(form.base_fields)
        return form


class CMFInlineMixin(CMFModelAdminMixin):
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        self._apply_crop_fields(formset.form.base_fields)
        return formset


class CMFStackedInline(CMFInlineMixin, StackedInline):
    pass


class CMFTabularInline(CMFInlineMixin, TabularInline):
    pass


# -----------------------------------------------------------------------
# Config admin
# -----------------------------------------------------------------------

class FieldsetField:
    def __init__(self, bound_field):
        self.field = bound_field
        self.is_checkbox = isinstance(bound_field.field.widget, forms.CheckboxInput)
        self.is_hidden = bound_field.field.widget.is_hidden

    def __str__(self):
        return str(self.field)

    @property
    def label_tag(self):
        label_class = "form-check-label" if self.is_checkbox else "form-label"
        if self.field.field.required:
            label_class += " required"
        return self.field.label_tag(attrs={"class": label_class})

    @property
    def help_text(self):
        return self.field.help_text

    @property
    def errors(self):
        return self.field.errors

    @property
    def id_for_label(self):
        return self.field.id_for_label


class FieldsetRow:
    def __init__(self, fields):
        self._fields = [FieldsetField(bf) for bf in fields]
        self.has_visible_field = any(not f.field.widget.is_hidden for f in fields)

    def __iter__(self):
        return iter(self._fields)


class FieldsetOptions:
    def __init__(self, fields, classes=(), description=None):
        self.fields = fields
        self.classes = " ".join(c for c in classes if c != "collapse")
        self.description = description
        self.is_collapsible = "collapse" in classes


@dataclass
class ExtraPanel:
    """
    Descriptor for an extra action panel attached to a ConfigModelAdmin page.

    Each instance renders a button on the config page. Clicking the button
    opens an offcanvas panel on the right side, whose content is provided
    by the specified template. The template is responsible for its own form
    action URL and submission handling.
    """
    label: str | Promise  # Button label displayed on the config page
    template: str  # Template path to include inside the offcanvas panel
    icon: str = ""  # Optional Tabler icon name, e.g. "mail", "settings"


class ConfigModelAdmin(CMFModelAdminMixin, ModelAdmin):
    """
    ModelAdmin subclass for kv-based configuration models (e.g. SiteConfig,
    EmailConfig).

    Instead of the standard changelist + change-page flow, this admin renders
    a single form page per category.  The form is built from CONFIG_SCHEMA via
    ConfigForm and persisted via ConfigService.

    Subclass usage::

        class SiteConfigAdmin(ConfigModelAdmin):
            form = SiteConfigForm
            fieldsets = [
                (_("Basic"), {"fields": ["site_name", "site_slogan"]}),
                (_("SEO"),   {"fields": ["seo_title", "seo_description"]}),
            ]

    The `form` attribute must be a ConfigForm subclass with `category` defined.
    `fieldsets` follows the exact same convention as standard ModelAdmin.
    """

    # Disable actions — config pages have no row-level operations.
    actions = None
    change_form_template = "config/change_form.html"
    form = None

    extra_panels: list[ExtraPanel] = []

    category: str | None = None

    def get_form_class(self):
        from djangocmf.cmfadmin.forms.config_forms import ConfigForm

        if self.form is not None:
            return self.form
        if self.category is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define 'category'."
            )
        # Auto-generate form from category.
        return type(
            f"{self.category.title()}ConfigForm",
            (ConfigForm,),
            {"category": self.category},
        )

    # -----------------------------------------------------------------------
    # Permission overrides
    # -----------------------------------------------------------------------

    def has_add_permission(self, request):
        # Config keys are defined in code, not created by users.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        # Remove E016: ConfigForm intentionally inherits from Form, not ModelForm.
        errors = [e for e in errors if e.id != 'admin.E016']
        return errors

    def _build_fieldsets(self, form):
        """
        Resolve fieldsets definition into (name, {fields: [BoundField]}) tuples.

        Supports the same field grouping syntax as ModelAdmin:
          - A plain string "field_name" → single field on its own line.
          - A tuple/list ("f1", "f2") → multiple fields on the same line.

        Returns a list of (name, {"fields": [[BoundField, ...], ...]}) where
        each inner list represents one form row.
        """
        fieldsets = self.fieldsets or [(None, {"fields": list(form.fields)})]
        result = []

        for name, options in fieldsets:
            rows = []
            for field_spec in options.get("fields", []):
                if isinstance(field_spec, (list, tuple)):
                    bound_fields = [form[f] for f in field_spec if f in form.fields]
                else:
                    bound_fields = [form[field_spec]] if field_spec in form.fields else []
                if bound_fields:
                    rows.append(FieldsetRow(bound_fields))

            result.append((
                name,
                FieldsetOptions(
                    fields=rows,
                    classes=options.get("classes", ()),
                    description=options.get("description"),
                )
            ))

        return result

    def changelist_view(self, request, extra_context=None):
        """
        renders the config form instead of a list.
        """
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        form_class = self.get_form_class()
        if form_class is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define 'form'."
            )

        if request.method == "POST":
            form = form_class(data=request.POST, files=request.FILES)
            if form.is_valid():
                form.save_resource()
                messages.success(request, _("Configuration saved successfully."))
                return HttpResponseRedirect(request.path)
        else:
            from djangocmf.cmfadmin.service.config import ConfigService

            initial = ConfigService.get_category(self.category)
            form = form_class(initial=initial)

        fieldsets = self._build_fieldsets(form)

        request.current_app = self.admin_site.name

        context = {
            **self.admin_site.each_context(request),
            "title": self.model._meta.verbose_name,
            "app_label": self.model._meta.app_label,
            "opts": self.model._meta,
            "form": form,
            "fieldsets": fieldsets,
            "media": self.media + form.media,
            "is_popup": False,
            "to_field": None,
            "preserved_filters": self.get_preserved_filters(request),
            "has_add_permission": self.has_add_permission(request),
            "has_change_permission": self.has_change_permission(request),
            "has_delete_permission": self.has_delete_permission(request),
            "has_view_permission": self.has_view_permission(request),
            "extra_panels": self.extra_panels,
            **(extra_context or {}),
        }

        return TemplateResponse(
            request,
            self.change_form_template,
            context,
        )
