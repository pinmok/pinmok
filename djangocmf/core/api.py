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
from django.utils.encoding import force_str
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


# Default HTTP status mapping for each ErrorCode.
# This is the single source of truth for error code → HTTP status resolution.
_DEFAULT_HTTP_STATUS: dict[ErrorCode, HTTPStatus] = {
    ErrorCode.SUCCESS: HTTPStatus.OK,
    ErrorCode.BAD_REQUEST: HTTPStatus.BAD_REQUEST,
    ErrorCode.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
    ErrorCode.FORBIDDEN: HTTPStatus.FORBIDDEN,
    ErrorCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCode.VALIDATION_ERROR: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCode.SERVER_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
}

# Default localized messages for each ErrorCode.
# Every ErrorCode MUST have an entry here — missing keys will raise KeyError immediately.
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
    """Resolve HTTP status from ErrorCode via lookup table."""
    return _DEFAULT_HTTP_STATUS.get(error_code, HTTPStatus.INTERNAL_SERVER_ERROR)


def _build_response(
        error_code: ErrorCode,
        message: str | Promise | None = None,
        data: Any = None,
        http_status: int | HTTPStatus | None = None,
) -> JsonResponse:
    """
    Internal response builder used by both success() and error().

    Response format:
      {
        "code": int,
        "message": str,
        "data": any
      }
    """
    if message is None:
        message = _DEFAULT_ERROR_MESSAGES[error_code]

    if data is None:
        data = {}

    if http_status is None:
        http_status = _infer_http_status(error_code)

    return JsonResponse(
        {
            "code": int(error_code),
            "message": force_str(message),
            "data": data,
        },
        status=http_status,
    )


def success(
        message: str | Promise | None = None,
        data: Any = None,
) -> JsonResponse:
    """Build a successful API response."""
    return _build_response(ErrorCode.SUCCESS, message=message, data=data)


def error(
        error_code: ErrorCode,
        message: str | Promise | None = None,
        data: Any = None,
        http_status: int | HTTPStatus | None = None,
) -> JsonResponse:
    """Build an error API response."""
    return _build_response(error_code, message=message, data=data, http_status=http_status)
