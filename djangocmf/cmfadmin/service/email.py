#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email module

Description:
  Provides a reusable email service for sending plain or template-based HTML emails.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-16
"""

import re

from django.core.mail import get_connection, EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin.backends import EmailConfig, EmailBackend
from djangocmf.cmfadmin.enums import ConfigCategory
from djangocmf.cmfadmin.service.config import ConfigService


class EmailValueError(ValueError):
    """Raised when email validation fails. Message is user-facing and translated."""
    pass


class EmailService:
    """
    Service for sending plain and template-based HTML emails.

    Uses the CMF EmailBackend if SMTP is configured in the database,
    otherwise falls back to Django's default connection.
    """

    def __init__(self, backend: str | BaseEmailBackend | None = None):
        """
        Initialize with an optional backend.
        Defaults to CMF EmailBackend if SMTP is configured, otherwise
        falls back to Django's default email connection.
        """
        if backend is None:
            self.backend = EmailBackend() if EmailConfig.get() else get_connection()
        elif isinstance(backend, BaseEmailBackend):
            self.backend = backend
        else:
            self.backend = get_connection(backend)

    @staticmethod
    def _render(template: str, context: dict[str, str]) -> str:
        """
        Replace ${var} placeholders in the template string.
        Unmatched placeholders are left as-is.
        """
        return re.sub(r"\${(\w+)}", lambda m: context.get(m.group(1), m.group(0)), template)

    @staticmethod
    def _load_config() -> dict:
        """Load typed email configuration from ConfigService."""
        return ConfigService.get_category(ConfigCategory.EMAIL)

    @property
    def from_email(self) -> str:
        """Return the configured default sender address."""
        return ConfigService.get(ConfigCategory.EMAIL, 'default_from_email') or ''

    def send(self, to: str | list[str], subject: str, content: str, from_email: str | None = None) -> int:
        """
        Send a plain HTML email to one or more recipients.

        Args:
            to: Recipient address or list of addresses.
            subject: Email subject line.
            content: Email body (HTML supported).
            from_email: Sender address. Falls back to default_from_email if not provided.

        Returns:
            Number of messages successfully sent.
        """
        if isinstance(to, str):
            to = [to]

        email = EmailMessage(
            subject=subject,
            body=content,
            to=to,
            from_email=from_email or self.from_email,
            connection=self.backend,
        )
        email.content_subtype = 'html'
        return email.send()

    def send_with_template(self, to: str | list[str], template_params: dict[str, str] | None = None) -> int:
        """
        Send an HTML email using the configured template.

        Subject, content, and sender are taken from the email config.
        If the template defines expected variables, template_params must
        supply all of them. Variable format in templates: ${var_name}.

        Args:
            to: Recipient address or list of addresses.
            template_params: Values for template variables, if any.

        Returns:
            Number of messages successfully sent.

        Raises:
            ValueError: If required template variables are missing.
        """
        config = self._load_config()

        # Assemble sender address with optional display name
        from_name = config.get('template_from_name', '').strip()
        from_email = self.from_email
        from_email_addr = f"{from_name} <{from_email}>" if from_name and from_email else from_email

        subject_template = config.get('template_subject', '')
        content_template = config.get('template_content', '')
        expected_vars = config.get('template_variables', '')

        # No variables defined — send template as-is
        if not expected_vars:
            return self.send(to, subject_template, content_template, from_email_addr)

        # Validate that all required variables are provided
        allowed_vars = [v.strip() for v in expected_vars.split(',') if v.strip()]
        if not template_params:
            raise EmailValueError(_("This email template requires variables, but none were provided."))

        missing = [var for var in allowed_vars if var not in template_params]
        if missing:
            raise EmailValueError(_('Missing required template variables: {}').format(', '.join(missing)))

        subject = self._render(subject_template, template_params)
        content = self._render(content_template, template_params)

        return self.send(to, subject, content, from_email_addr)
