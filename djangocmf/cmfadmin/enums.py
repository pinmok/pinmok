#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enums module

Description:
  cmfadmin enumeration classes.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-15
"""
from enum import StrEnum

from django.db import models
from django.utils.translation import gettext_lazy as _


class FileType(models.TextChoices):
    IMAGE = "image", _("image")
    VIDEO = "video", _("video")
    AUDIO = "audio", _("audio")
    DOCUMENT = "document", _("document")
    ARCHIVE = "archive", _("archive")


class MimeType(models.TextChoices):
    # Image types
    JPEG = 'image/jpeg', 'JPEG'
    PNG = 'image/png', 'PNG'
    GIF = 'image/gif', 'GIF'
    WEBP = 'image/webp', 'WEBP'
    BMP = 'image/bmp', 'BMP'
    SVG = 'image/svg+xml', 'SVG'
    AVIF = 'image/avif', 'AVIF'

    # Audio types
    MP3 = 'audio/mpeg', 'MP3'
    WAV = 'audio/wav', 'WAV'
    OGG = 'audio/ogg', 'OGG'
    FLAC = 'audio/flac', 'FLAC'
    AAC = 'audio/aac', 'AAC'
    OPUS = 'audio/opus', 'OPUS'

    # Video types
    MP4 = 'video/mp4', 'MP4'
    WEBM = 'video/webm', 'WEBM'
    AVI = 'video/x-msvideo', 'AVI'
    MOV = 'video/quicktime', 'MOV'
    MKV = 'video/x-matroska', 'MKV'
    OGV = 'video/ogg', 'OGV'

    # Document types
    PDF = 'application/pdf', 'PDF'
    DOC = 'application/msword', 'DOC'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'DOCX'
    XLS = 'application/vnd.ms-excel', 'XLS'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'XLSX'
    PPT = 'application/vnd.ms-powerpoint', 'PPT'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'PPTX'
    TXT = 'text/plain', 'TXT'

    # Compressed / archive types
    ZIP = 'application/zip', 'ZIP'
    RAR = 'application/vnd.rar', 'RAR'
    SEVEN_Z = 'application/x-7z-compressed', '7Z'
    TAR = 'application/x-tar', 'TAR'
    GZIP = 'application/gzip', 'GZ'

    @classmethod
    def to_extensions(cls, mimes: list[str]) -> list[str]:
        """Convert a list of MIME strings to human-readable extension labels."""
        mime_map = {str(m.value): m.label for m in cls}
        result = []
        for mime in mimes:
            if mime in mime_map:
                result.append(mime_map[mime])
            else:
                # Fallback: strip prefix, e.g. 'application/pdf' -> 'pdf'
                result.append(mime.split('/')[-1])
        return result


class ConfigCategory(models.TextChoices):
    SITE = "site", "Site Information"
    EMAIL = "email", "Email Settings"
    UPLOAD = "upload", "Upload Settings"
    FILE = "file", "File Management"
    ICONS = 'icons', 'Icons Management'
    TEMPLATE = 'template', 'Template Management'
    SYSTEM = 'system', 'System Settings'
    LOG = 'log', 'Log Management'
    NAV = 'nav', 'Navigations'
    LINKS = 'links', 'External Links'


class UploadConfigKey(StrEnum):
    IMAGE_SIZE = 'upload_image_size'
    IMAGE_TYPE = 'upload_image_type'
    AUDIO_SIZE = 'upload_audio_size'
    AUDIO_TYPE = 'upload_audio_type'
    VIDEO_SIZE = 'upload_video_size'
    VIDEO_TYPE = 'upload_video_type'
    DOCUMENT_SIZE = 'upload_document_size'
    DOCUMENT_TYPE = 'upload_document_type'
    ARCHIVE_SIZE = 'upload_archive_size'
    ARCHIVE_TYPE = 'upload_archive_type'
    UPLOAD_PATH_RULE = 'upload_path_rule'
    UPLOAD_MAX_FILES = 'upload_max_files'


class ConfigType(StrEnum):
    """
    Markers used by ConfigService and Form generator.

    STR          → CharField (single line)
    TEXT         → Textarea (multi-line)
    INT          → IntegerField; Service converts stored string to int on read.
                   Empty string is treated as None (no value), not converted.
    FLOAT        → FloatField; same conversion rule as INT.
    BOOL         → BooleanField; stored as "true"/"false", converted on read.
    JSON         → Textarea; stored as JSON string, parsed to dict/list on read.
    DATETIME     → DateTimeField; stored as ISO string, converted on read.
    IP           → GenericIPAddressField (validation only, stored as str).
    URL          → URLField (validation only, stored as str).
    EMAIL        → EmailField (validation only, stored as str).
    IMAGE        → Custom image crop/upload widget.
    FILE         → Custom file upload widget.
    MULTI_SELECT → Multi-select widget; stored as comma-separated string,
                   returned as list on read. Requires "choices" field.
    """
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    TEXT = "text"
    JSON = "json"
    DATETIME = "datetime"
    IP = "ip"
    URL = "url"
    EMAIL = "email"
    IMAGE = "image"
    FILE = "file"
    MULTI_SELECT = "multi_select"


class UploadPathRule(StrEnum):
    """Defines strategies for organizing uploaded files into subdirectories."""
    MONTH = 'month'
    DATE = 'date'

    @property
    def label(self):
        labels = {
            self.DATE: _('By Date: YYYY/MM/DD — For frequent uploads'),
            self.MONTH: _('By Month: YYYY/MM — For blogs or infrequent uploads'),
        }
        return labels[self]


class TargetChoices(models.TextChoices):
    """ HTML a tag target attribute """
    SELF = '_self', _('Self Window')
    BLANK = '_blank', _('Blank Window')


class ImageWidgetMode(StrEnum):
    PATH = 'path'
    RESOURCE = 'resource'


class NavType(models.TextChoices):
    MAIN = "main", _("Main Navigation")
    FOOTER = "footer", _("Footer Navigation")
    SIDEBAR = "sidebar", _("Sidebar Navigation")
