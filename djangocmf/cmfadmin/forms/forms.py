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
from django.contrib.admin.forms import AdminPasswordChangeForm
from django.contrib.auth.forms import AdminPasswordChangeForm as AuthPasswordChangeForm, AdminUserCreationForm
from django.contrib.auth.forms import SetUnusablePasswordMixin
from django.forms.widgets import Select
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin.models import Nav
from djangocmf.cmfadmin.widgets import CMFPassword, CMFRadioSelect


class CMFAdminPasswordResetForm(AuthPasswordChangeForm):
    """
    Custom password change form for CMF admin.
    Replaces the default RadioSelect widget with CMFRadioSelect for Tabler styling.
    """
    usable_password_help_text = SetUnusablePasswordMixin.usable_password_help_text + (
        '<div id="id_unusable_warning" class="messagelist alert alert-warning mt-2 mb-0">'
        '<div class="alert-icon">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon alert-icon">'
        '<path d="M12 9v4"></path>'
        '<path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0z"></path>'
        '<path d="M12 16h.01"></path></svg></div>'
        f'{_("If disabled, the current password for this user will be lost.")}</div>'
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["password1"].widget = CMFPassword(attrs={"autocomplete": "new-password"})
        self.fields["password2"].widget = CMFPassword(attrs={"autocomplete": "new-password"})
        if 'usable_password' in self.fields:
            attrs = {"class": "form-check-input inline"}
            # Replacing the widget does not trigger the choices setter,
            # so choices must be passed explicitly to the new widget.
            choices = self.fields['usable_password'].widget.choices
            self.fields['usable_password'].widget = CMFRadioSelect(attrs=attrs, choices=choices)


class CMFAdminUserCreationForm(AdminUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget = CMFPassword(attrs={"autocomplete": "new-password"})
        self.fields["password2"].widget = CMFPassword(attrs={"autocomplete": "new-password"})
        if 'usable_password' in self.fields:
            choices = self.fields['usable_password'].widget.choices
            self.fields['usable_password'].widget = CMFRadioSelect(attrs={"class": "form-check-input inline"}, choices=choices)


class CMFAdminPasswordChangeForm(AdminPasswordChangeForm):
    """
    Custom password change form for CMF admin.
    Replaces default PasswordInput widgets with CMFPasswordInput for Tabler styling.
    Handles old_password, new_password1, and new_password2 fields.
    """

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["old_password"].widget = CMFPassword(attrs={"autocomplete": "current-password", "autofocus": True})
        self.fields["new_password1"].widget = CMFPassword(attrs={"autocomplete": "new-password"})
        self.fields["new_password2"].widget = CMFPassword(attrs={"autocomplete": "new-password"})


class CMFActionForm(forms.Form):
    """
    Custom action form for CMF admin list view.
    Applies Tabler styling to the action dropdown and hidden select_across field.
    """
    action = forms.ChoiceField(
        label=_("Action:"),
        widget=Select(attrs={'class': 'form-select form-select-sm w-auto'}),
    )
    select_across = forms.BooleanField(
        label="",
        required=False,
        initial=0,
        widget=forms.HiddenInput({"class": "select-across"}),
    )


class NavForm(forms.ModelForm):
    class Meta:
        model = Nav
        fields = ['nav_type', 'parent', 'url', 'icon', 'target', 'sort_order', 'is_visible']

    def __init__(self, *args, **kwargs):
        nav_type = kwargs.pop('nav_type', None)
        super().__init__(*args, **kwargs)

        qs = Nav.objects.all()
        if nav_type:
            qs = qs.filter(nav_type=nav_type)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        self.fields['parent'].queryset = qs
        self.fields['parent'].required = False
        self.fields['parent'].widget.attrs['data-allow-null'] = 'true'
