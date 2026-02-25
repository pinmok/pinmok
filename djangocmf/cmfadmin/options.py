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

from django import forms
from django.contrib import admin
from django.contrib.admin.options import get_ul_class
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.utils.translation import gettext as _

from djangocmf.cmfadmin import widgets
from djangocmf.cmfadmin.widgets import CMFTextarea


class CMFModelAdmin(admin.ModelAdmin):
    """
    CMF default ModelAdmin.

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
        models.ImageField: {"widget": widgets.CMFImageFileInput},
        models.FileField: {"widget": widgets.CMFFileInput},
        models.EmailField: {"widget": widgets.CMFEmailInput},
        models.UUIDField: {"widget": widgets.CMFUUIDInput},
        models.BooleanField: {"widget": widgets.CMFCheckboxInput},
        models.GenericIPAddressField: {"widget": widgets.CMFGenericIPAddress},
        models.JSONField: {'widget': CMFTextarea},
    }

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
        """
        db = kwargs.get("using")

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
