#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mixins module

Description:
  Reusable mixins for class-based views.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026-03-12
"""
from django.conf import settings
from django.shortcuts import redirect

from pinmok.core.api import ErrorCode, error
from pinmok.core.permission import permission_checker


class PinmokPermissionMixin:
    """
    Permission mixin for class-based views.

    Checks permission before dispatching the request.
    - AJAX requests receive a JSON 401 response.
    - Regular requests are redirected to the login page.

    Usage:
      class MyView(PinmokPermissionMixin, View):
          permission = 'myapp.can_do_something'  # optional

    Set permission = None to use the default checker without a specific permission.
    """

    permission: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not permission_checker.check(request, permission=self.permission):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return error(ErrorCode.UNAUTHORIZED)
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)
