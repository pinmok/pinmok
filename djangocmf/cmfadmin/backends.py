#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backends module

Description:
  CMF custom email backend for dynamic SMTP configuration.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from djangocmf.cmfadmin.enums import ConfigCategory
from djangocmf.cmfadmin.models import Config


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
        ssl_keyfile (str | None): Path to SSL key file.
        ssl_certfile (str | None): Path to SSL certificate file.

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
    ssl_keyfile: str | None = None
    ssl_certfile: str | None = None

    @classmethod
    def get(cls) -> dict[str, Any]:
        """
        Fetch email config from database.
        Return empty dict if not configured or incomplete.
        """
        cache_key = "email_backend_config"
        cached_config = cache.get(cache_key)
        if cached_config is not None:
            return cached_config

        try:
            email_configs_from_db = Config.objects.filter(category=ConfigCategory.EMAIL).values('key', 'value')
            if not email_configs_from_db.exists():
                return {}

            data = {r['key']: r['value'] for r in email_configs_from_db}
            if not data.get('email_host'):
                return {}

            # Validate port if present
            port = None
            if data.get('email_port'):
                try:
                    port = int(data.get('email_port'))
                    if not (0 < port <= 65535):
                        return {}
                except ValueError:
                    return {}
            config_obj = cls(
                host=data.get('email_host'),
                port=port,
                username=data.get('email_host_user'),
                password=data.get('email_host_password'),
                use_tls=data.get('email_use_tls') == 'on',
                use_ssl=data.get('email_use_ssl') == 'on',
                timeout=int(data.get('email_timeout')) if data.get('email_timeout') else None,
            )
            if config_obj.use_tls and config_obj.use_ssl:
                return {}

            config_dict = config_obj.to_dict()
            cache.set(cache_key, config_dict, timeout=3600)
            return config_dict
        except Exception as e:
            return {}

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class EmailBackend(SMTPBackend):
    """
    Custom EmailBackend that overrides settings-based configuration
    with values fetched from the database, if settings are not explicitly defined.
    """

    def __init__(self, *args, **kwargs):
        backend_config = EmailConfig.get()
        if backend_config:
            kwargs.update(backend_config)
        super().__init__(*args, **kwargs)
