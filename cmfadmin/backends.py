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

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


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
        # TODO 处理逻辑
        config_obj = cls(
            host='smtp.gmail.com',
            port=587,
        )
        return config_obj.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class EmailBackend(SMTPBackend):
    """
    Custom EmailBackend that overrides settings-based configuration
    with values fetched from the database, if settings are not explicitly defined.
    """

    def __init__(self, *args, **kwargs):
        if not getattr(settings, 'EMAIL_HOST', None):
            kwargs.update(EmailConfig.get())
        super().__init__(*args, **kwargs)
