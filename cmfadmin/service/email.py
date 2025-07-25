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

from django.core.cache import cache
from django.core.mail import get_connection, EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.translation import gettext_lazy as _

from cmfadmin.backends import EmailConfig, EmailBackend
from cmfadmin.enums import ConfigCategory
from cmfadmin.models import Config


class EmailService:
    def __init__(self, backend: str | BaseEmailBackend | None = None):
        """
        Initialize the email service with optional default sender and backend.
        Backend defaults to console output if not provided.
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
        Replace variables in the template using ${var} format.
        If a variable is not found, keep the placeholder.
        """
        return re.sub(r"\${(\w+)}", lambda m: context.get(m.group(1), m.group(0)), template)

    @staticmethod
    def _load_config() -> dict[str, str]:
        """
        Load email-related configuration from the database.
        Returns a flat dict of key-value pairs.
        """
        cache_key = "email_template_config"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        config = Config.objects.filter(category=ConfigCategory.EMAIL_TEMPLATE).values('key', 'value')
        result = {item['key']: item['value'] for item in config}
        cache.set(cache_key, result, timeout=3600)
        return result

    @property
    def from_email(self) -> str:
        return Config.objects.filter(key='default_from_email').values_list('value', flat=True).first()

    def send(self, to: str | list[str], subject: str, content: str, from_email: str | None = None) -> int:
        """
        Send a basic HTML email to one or more recipients.
        If from_email is not provided, fallback to default from_email.
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
        Send an email using a configured template.

        - Subject, content, and sender come from Config.
        - If template defines variables, template_params must provide them.
        - Variable format in templates: ${var_name}
        """
        config = self._load_config()

        # Assemble the from address with optional display name
        from_name = config.get('template_from_name', '').strip()
        from_email = self.from_email
        from_email_addr = f"{from_name} <{from_email}>" if from_email else from_email

        # Get template subject/content
        subject_template = config.get('template_subject', '')
        content_template = config.get('template_content', '')
        expected_vars = config.get('template_variables', '')

        # No variables configured → send as-is
        if not expected_vars:
            subject = subject_template
            content = content_template
            return self.send(to, subject, content, from_email_addr)

        # Parse allowed variable names
        allowed_vars = [v.strip() for v in expected_vars.split(',') if v.strip()]
        if not template_params:
            raise ValueError(_("This email template requires variables, but none were provided."))

        # Check for missing variables
        missing = [var for var in allowed_vars if var not in template_params]
        if missing:
            raise ValueError(_("Missing required template variables: ") + ", ".join(missing))

        # Render subject/content with variables
        subject = self._render(subject_template, template_params)
        content = self._render(content_template, template_params)

        return self.send(to, subject, content, from_email_addr)
