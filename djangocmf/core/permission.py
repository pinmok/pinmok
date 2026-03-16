#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
permission module

Description:
  Provides a pluggable permission checking mechanism.
  The default checker requires is_staff. Third-party apps can register
  their own checker via permission_checker.register() in AppConfig.ready().

  Example:
    from djangocmf.core.permission import permission_checker

    class MyAppConfig(AppConfig):
        def ready(self):
            from djangocmf.core.permission import permission_checker
            from myapp.auth import my_checker
            permission_checker.register(my_checker)

  Checker signature:
    def my_checker(request, permission: str | None = None) -> bool: ...

Author:
  惠达浪 <crazys@126.com>
Created:
  2026-03-12
"""
from typing import Callable

from django.http import HttpRequest


def _default_checker(request: HttpRequest, permission: str | None = None) -> bool:
    """Default permission checker: requires authenticated staff user."""
    return request.user.is_authenticated and request.user.is_staff


class PermissionChecker:
    """
    A pluggable permission checker with a single registered handler.

    Third-party apps register their own checker via register().
    Falls back to the default checker (is_staff) if none is registered.
    """

    def __init__(self):
        self._checker: Callable = _default_checker

    def register(self, func: Callable) -> Callable:
        """
        Register a custom permission checker function.
        Can be used as a decorator or called directly.

        The checker must match this signature:
          def checker(request, permission=None) -> bool: ...
        """
        self._checker = func
        return func

    def check(self, request: HttpRequest, permission: str | None = None) -> bool:
        """Check permission for the given request."""
        return self._checker(request, permission=permission)


# Global singleton — import this everywhere
permission_checker = PermissionChecker()
