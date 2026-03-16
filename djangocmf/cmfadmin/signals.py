#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signals module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2026/3/11
"""
from django.contrib.auth.models import User, Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from djangocmf.cmfadmin.service.menu import AdminMenuManager


def _clear_menu_cache_on_permission_change(action: str) -> None:
    """
    Clear the admin menu cache if the signal action modifies permissions.

    Only post-action signals (post_add, post_remove, post_clear) trigger
    a cache clear, pre-action signals are ignored.
    """
    if action in frozenset({"post_add", "post_remove", "post_clear"}):
        AdminMenuManager.clear_admin_menu_cache()


@receiver(m2m_changed, sender=User.groups.through)
def user_groups_changed(sender, instance, action, **kwargs):
    """
    Triggered when a user's group membership changes.
    """
    _clear_menu_cache_on_permission_change(action)


@receiver(m2m_changed, sender=User.user_permissions.through)
def user_permissions_changed(sender, instance, action, **kwargs):
    """
    Triggered when a user's direct permissions change.
    """
    _clear_menu_cache_on_permission_change(action)


@receiver(m2m_changed, sender=Group.permissions.through)
def group_permissions_changed(sender, instance, action, **kwargs):
    """
    Triggered when a group's permissions change.
    """
    _clear_menu_cache_on_permission_change(action)
