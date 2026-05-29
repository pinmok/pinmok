#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backends module

Description:
  Pinmok custom email backend for dynamic SMTP configuration.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

logger = logging.getLogger(__name__)


class EmailBackend(SMTPBackend):
    """
    Custom EmailBackend that overrides settings-based configuration
    with values fetched from the database, if settings are not explicitly defined.
    """

    def __init__(self, *args, **kwargs):
        from pinmok.padmin.service.email import EmailConfig

        backend_config = EmailConfig.get()
        if backend_config:
            kwargs.update(backend_config)
        # If no database config is available, fall back to Django's default
        # settings (EMAIL_HOST, EMAIL_PORT, etc.) via the parent constructor.
        super().__init__(*args, **kwargs)
