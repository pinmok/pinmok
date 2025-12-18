#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api module

Description:
  Minimal, reusable API utilities for standardized JSON responses and stable error codes.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-12-17
"""
from enum import IntEnum
from http import HTTPStatus
from typing import Any

from django.http import JsonResponse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


class ErrorCode(IntEnum):
    """
    API error codes.

    These codes are part of the public API contract and
    MUST remain backward compatible once released.
    """
    SUCCESS = 0

    BAD_REQUEST = 40001
    UNAUTHORIZED = 40101
    FORBIDDEN = 40301
    NOT_FOUND = 40404
    VALIDATION_ERROR = 42201
    SERVER_ERROR = 50001


# Default HTTP status mapping for each ErrorCode
_DEFAULT_HTTP_STATUS: dict[ErrorCode, HTTPStatus] = {
    ErrorCode.SUCCESS: HTTPStatus.OK,
    ErrorCode.BAD_REQUEST: HTTPStatus.BAD_REQUEST,
    ErrorCode.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
    ErrorCode.FORBIDDEN: HTTPStatus.FORBIDDEN,
    ErrorCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCode.VALIDATION_ERROR: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCode.SERVER_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
}

# Default localized messages for each ErrorCode
_DEFAULT_ERROR_MESSAGES: dict[ErrorCode, Promise] = {
    ErrorCode.SUCCESS: _("Success"),
    ErrorCode.BAD_REQUEST: _("Bad request."),
    ErrorCode.UNAUTHORIZED: _("Unauthorized."),
    ErrorCode.FORBIDDEN: _("Permission denied."),
    ErrorCode.NOT_FOUND: _("Resource not found."),
    ErrorCode.VALIDATION_ERROR: _("Validation failed."),
    ErrorCode.SERVER_ERROR: _("Internal server error."),
}


def _infer_http_status(error_code: ErrorCode) -> HTTPStatus:
    """
    Infer HTTP status from ErrorCode category.

    This function MUST NOT grow as ErrorCode grows.
    """
    code = int(error_code)

    if code == 0:
        return HTTPStatus.OK

    # Validation errors (user can fix input)
    if 42200 <= code < 42300:
        return HTTPStatus.UNPROCESSABLE_ENTITY

    # Client / business errors
    if 40000 <= code < 50000:
        return HTTPStatus.BAD_REQUEST

    # Server errors
    if 50000 <= code < 60000:
        return HTTPStatus.INTERNAL_SERVER_ERROR

    # Fallback (should never happen)
    return HTTPStatus.INTERNAL_SERVER_ERROR


def success(
        message: str | Promise | None = None,
        data: dict[str, Any] | None = None,
) -> JsonResponse:
    """
    Build a successful API response.
    """
    return error(error_code=ErrorCode.SUCCESS, message=message, data=data)


def error(
        error_code: ErrorCode,
        message: str | Promise | None = None,
        data: dict[str, Any] | None = None,
        http_status: int | HTTPStatus | None = None,
) -> JsonResponse:
    """
    Unified API JSON response builder.

    - Maps error codes to HTTP status automatically
    - Provides default, translatable messages
    - Ensures JSON-serializable output
    """
    if message is None:
        message = _DEFAULT_ERROR_MESSAGES.get(error_code, _('Error'))

    # Ensure lazy translation objects are JSON serializable
    if isinstance(message, Promise):
        message = str(message)

    if data is None:
        data = {}

    if http_status is None:
        http_status = _infer_http_status(error_code)

    return JsonResponse(
        {
            "code": int(error_code),
            "message": message,
            "data": data,
        },
        status=http_status,
    )
