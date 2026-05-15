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
from dataclasses import dataclass
from typing import Any

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from pinmok.padmin.enums import ConfigCategory
from pinmok.padmin.service.config import ConfigService

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """
    EmailConfig

    This class defines the structure for email configuration values
    used by the custom EmailBackend. It acts as a value object for
    carrying SMTP configuration data, decoupled from Django settings.

    Attributes:
        host (str): SMTP server address (required).
        port (int | None): SMTP server port number.
        username (str | None): SMTP authentication username.
        password (str | None): SMTP authentication password.
        use_tls (bool): Whether to use TLS (default: False).
        use_ssl (bool): Whether to use SSL (default: False).
        timeout (int | None): Optional socket timeout in seconds.
        ssl_key_file (str | None): Path to SSL key file.
        ssl_cert_file (str | None): Path to SSL certificate file.

    Class Methods:
        get() -> dict[str, Any]:
            Returns a dictionary of email configuration values.
            In production, this method should fetch configuration
            from the database or other persistent storage.

    Instance Methods:
        to_dict() -> dict[str, Any]:
            Converts the EmailConfig instance into a dictionary.
    """
    host: str
    port: int | None = None
    username: str | None = None
    password: str | None = None
    use_tls: bool = False
    use_ssl: bool = False
    timeout: int | None = None
    ssl_key_file: str | None = None
    ssl_cert_file: str | None = None

    @classmethod
    def get(cls) -> dict[str, Any]:
        """
        Fetch SMTP configuration from the database via ConfigService.
        Returns an empty dict if the host is not configured or
        SSL and TLS are both enabled (invalid combination).
        """
        try:
            data = ConfigService.get_category(ConfigCategory.EMAIL)

            host = data.get('smtp_host', '')
            if not host:
                return {}

            port = data.get('smtp_port')
            use_ssl = data.get('smtp_use_ssl', False)
            use_tls = data.get('smtp_use_tls', False)

            # Invalid combination — refuse to proceed
            if use_ssl and use_tls:
                return {}

            timeout_raw = data.get('timeout', '0')
            timeout = None if timeout_raw == '0' else int(timeout_raw)

            config_obj = cls(
                host=host,
                port=port,
                username=data.get('smtp_username') or None,
                password=data.get('smtp_password') or None,
                use_tls=use_tls,
                use_ssl=use_ssl,
                timeout=timeout,
            )
            return config_obj.to_dict()

        except Exception as e:
            logger.warning('Failed to load email config: %s', e)
            return {}

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class EmailBackend(SMTPBackend):
    """
    Custom EmailBackend that overrides settings-based configuration
    with values fetched from the database, if settings are not explicitly defined.
    """

    def __init__(self, *args, **kwargs):
        backend_config = EmailConfig.get()
        if backend_config:
            kwargs.update(backend_config)
        # If no database config is available, fall back to Django's default
        # settings (EMAIL_HOST, EMAIL_PORT, etc.) via the parent constructor.
        super().__init__(*args, **kwargs)
