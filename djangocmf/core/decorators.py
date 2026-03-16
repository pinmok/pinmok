#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decorators module

Description:
  Reusable decorators for function-based views.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026-03-12
"""
import functools

from django.conf import settings
from django.shortcuts import redirect

from djangocmf.core.api import ErrorCode, error
from djangocmf.core.permission import permission_checker


def permission_required(permission: str | None = None):
    """
    Decorator for function-based views.

    Checks permission before calling the view function.
    - AJAX requests receive a JSON 401 response.
    - Regular requests are redirected to the login page.

    Usage:
      @permission_required()
      def my_view(request): ...

      @permission_required('myapp.can_upload')
      def my_view(request): ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not permission_checker.check(request, permission=permission):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return error(ErrorCode.UNAUTHORIZED)
                return redirect(settings.LOGIN_URL)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
