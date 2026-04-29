#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_schema

Description:
  Defines CONFIG_SCHEMA — the single source of truth for all configuration items.
  This is a custom structure parsed by ConfigService (type conversion) and Form
  generator (field rendering). It is NOT a Django built-in.

  Each category maps to a dict of keys with the following attributes:

    type        (required) Controls Form field type and Service value conversion.
                See ConfigType for available values.
    default     (required) Fallback value when the key is not found in DB.
                Must match the storage format (str for most types, comma-separated
                str for MULTI_SELECT).
    label       (required) Form field label. Use lowercase; abbreviations (SMTP,
                SSL, URL) stay uppercase. Translation via gettext_lazy.
    required    (optional, default False) Whether the field must be non-empty.
    choices     (optional) List of (value, display) tuples. Presence of this field
                causes the Form generator to render a select or multi-select widget.
    help_text   (optional) Hint text displayed below the form field.

Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""

from django.utils.translation import gettext_lazy as _

from djangocmf import core
from djangocmf.cmfadmin.enums import MimeType, UploadConfigKey, ConfigCategory, ConfigType, UploadPathRule

CONFIG_SCHEMA = {

    # -------------------------------------------------------------------------
    # Site information
    # -------------------------------------------------------------------------
    ConfigCategory.SITE: {
        "site_name": {
            "type": ConfigType.STR,
            "default": core.__title__,
            "label": _("Site name"),
            "required": True,
            "help_text": _("The name of the site, displayed next to the logo in the top-left corner."),
        },
        "site_slogan": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Site slogan"),
            "help_text": _("A short tagline displayed near the site logo or page title."),
        },
        "site_logo": {
            "type": ConfigType.IMAGE,
            "default": "",
            "label": _("Site logo"),
            "help_text": _('After uploading, click "Save" below for it to take effect.'),
        },
        "icp": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("ICP filing number"),
            "help_text": _("Leave this field blank if you don't have the number."),
        },
        "pns": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Public Security Internet Filing Number"),
            "help_text": _("Public Security Internet Filing Number, leave blank if not applicable."),
        },
        "service_phone": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Service phone"),
        },
        "service_email": {
            "type": ConfigType.EMAIL,
            "default": "",
            "label": _("Service email"),
        },
        "contact_address": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Contact address"),
        },
        "wechat_qrcode": {
            "type": ConfigType.IMAGE,
            "default": "",
            "label": _("WeChat QR code"),
            "help_text": _('After uploading, click "Save" below for it to take effect.'),
        },
        "wechat_mini_program": {
            "type": ConfigType.IMAGE,
            "default": "",
            "label": _("WeChat Mini Program"),
            "help_text": _('After uploading, click "Save" below for it to take effect.'),
        },
        "wechat_official_account": {
            "type": ConfigType.IMAGE,
            "default": "",
            "label": _("WeChat Official Account"),
            "help_text": _('After uploading, click "Save" below for it to take effect.'),
        },
        "facebook_link": {
            "type": ConfigType.URL,
            "default": "",
            "label": _("Facebook link"),
        },
        "x_link": {
            "type": ConfigType.URL,
            "default": "",
            "label": _("X link"),
        },
        "linkedin_link": {
            "type": ConfigType.URL,
            "default": "",
            "label": _("LinkedIn link"),
        },
        "instagram_link": {
            "type": ConfigType.URL,
            "default": "",
            "label": _("Instagram link"),
        }
    },

    # -------------------------------------------------------------------------
    # Email settings + templates (merged into one category)
    # -------------------------------------------------------------------------
    ConfigCategory.EMAIL: {
        # SMTP connection
        "smtp_host": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("SMTP host"),
            "required": True,
            "help_text": _("The address of your email server."),
        },
        "smtp_port": {
            "type": ConfigType.INT,
            "default": 465,
            "label": _("SMTP port"),
            "required": True,
            "help_text": _("Common ports: 587 (recommended), 465 (126/163/QQ mail), 25, 2525."),
        },
        "smtp_use_ssl": {
            "type": ConfigType.BOOL,
            "default": True,
            "label": _("Use SSL"),
        },
        "smtp_use_tls": {
            "type": ConfigType.BOOL,
            "default": False,
            "label": _("Use TLS"),
        },
        "smtp_username": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("SMTP username"),
        },
        "smtp_password": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("SMTP password"),
        },
        "default_from_email": {
            "type": ConfigType.EMAIL,
            "default": "",
            "label": _("From email address"),
            "required": True,
            "help_text": _("The email address used as the sender for outgoing emails."),
        },
        # Empty string means no timeout; ConfigService returns None when value is "".
        "timeout": {
            "type": ConfigType.STR,
            "default": "0",
            "label": _("Timeout"),
            "required": True,
            "choices": [
                ("0", _("default")),
                ("30", _("30 seconds")),
                ("60", _("60 seconds")),
            ],
            "help_text": _("Maximum seconds to wait for the mail server to respond, leave empty for no limit."),
        },

        # Email template
        "template_from_name": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("From name"),
            "help_text": _("The name displayed as the sender in the recipient's inbox."),
        },
        "template_subject": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Subject"),
        },
        "template_content": {
            "type": ConfigType.TEXT,
            "default": "",
            "label": _("Content"),
            "help_text": _("Email body, supports HTML formatting."),
        },
        "template_variables": {
            "type": ConfigType.STR,
            "default": "",
            "label": _("Available variables"),
            "help_text": _("List of variables you can use within this template."),
        },
    },

    # -------------------------------------------------------------------------
    # Upload settings — one size + one allowed-type entry per file category.
    # Size unit: MB. Types stored as comma-separated MIME strings.
    # -------------------------------------------------------------------------
    ConfigCategory.UPLOAD: {
        UploadConfigKey.UPLOAD_MAX_FILES: {
            "type": ConfigType.INT,
            "default": 10,
            "label": _("Max files per upload"),
            "required": True,
            "help_text": _("Maximum number of files a user can upload at once."),
        },

        # Image
        UploadConfigKey.IMAGE_SIZE: {
            "type": ConfigType.INT,
            "default": 5,
            "label": _("Max image file size"),
        },
        UploadConfigKey.IMAGE_TYPE: {
            "type": ConfigType.MULTI_SELECT,
            "default": f"{MimeType.JPEG.value},{MimeType.PNG.value},{MimeType.SVG.value}",
            "label": _("Allowed image types"),
            "choices": [(m.value, m.label) for m in
                        [MimeType.JPEG, MimeType.PNG, MimeType.GIF, MimeType.WEBP, MimeType.BMP, MimeType.SVG, MimeType.AVIF]],
        },

        # Audio
        UploadConfigKey.AUDIO_SIZE: {
            "type": ConfigType.INT,
            "default": 10,
            "label": _("Max audio file size"),
        },
        UploadConfigKey.AUDIO_TYPE: {
            "type": ConfigType.MULTI_SELECT,
            "default": f"{MimeType.MP3.value},{MimeType.WAV.value}",
            "label": _("Allowed audio types"),
            "choices": [(m.value, m.label) for m in
                        [MimeType.MP3, MimeType.WAV, MimeType.OGG, MimeType.FLAC, MimeType.AAC, MimeType.OPUS]],
        },

        # Video
        UploadConfigKey.VIDEO_SIZE: {
            "type": ConfigType.INT,
            "default": 30,
            "label": _("Max video file size"),
        },
        UploadConfigKey.VIDEO_TYPE: {
            "type": ConfigType.MULTI_SELECT,
            "default": f"{MimeType.MP4.value}",
            "label": _("Allowed video types"),
            "choices": [(m.value, m.label) for m in
                        [MimeType.MP4, MimeType.WEBM, MimeType.AVI, MimeType.MOV, MimeType.MKV, MimeType.OGV]],
        },

        # Document
        UploadConfigKey.DOCUMENT_SIZE: {
            "type": ConfigType.INT,
            "default": 10,
            "label": _("Max document file size"),
        },
        UploadConfigKey.DOCUMENT_TYPE: {
            "type": ConfigType.MULTI_SELECT,
            "default": f"{MimeType.PDF.value},{MimeType.DOCX.value},{MimeType.XLSX.value},{MimeType.TXT.value}",
            "label": _("Allowed document types"),
            "choices": [(m.value, m.label) for m in
                        [MimeType.PDF, MimeType.DOC, MimeType.DOCX, MimeType.XLS,
                         MimeType.XLSX, MimeType.PPT, MimeType.PPTX, MimeType.TXT]],
        },

        # Archive
        UploadConfigKey.ARCHIVE_SIZE: {
            "type": ConfigType.INT,
            "default": 10,
            "label": _("Max archive file size"),
        },
        UploadConfigKey.ARCHIVE_TYPE: {
            "type": ConfigType.MULTI_SELECT,
            "default": f"{MimeType.ZIP.value},{MimeType.RAR.value}",
            "label": _("Allowed archive types"),
            "choices": [(m.value, m.label) for m in
                        [MimeType.ZIP, MimeType.RAR, MimeType.SEVEN_Z, MimeType.TAR, MimeType.GZIP]],
        },
        UploadConfigKey.UPLOAD_PATH_RULE: {
            "type": ConfigType.STR,
            "default": UploadPathRule.MONTH,
            "label": _("Upload path rule"),
            "choices": [(r, r.label) for r in UploadPathRule],
            "help_text": _("Determines the directory structure for uploaded files on the server.")
        },
    },
    # Other configs
}
