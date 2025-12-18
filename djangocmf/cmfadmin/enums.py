#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enums module

Description:
  Centralized module for all project-wide enumeration classes.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-15
"""
from enum import StrEnum, Enum

from django.db import models


# Menu sync modes
class MenuSyncMode(StrEnum):
    SYNC_ALL = 'all'


# Menu data sources
class MenuSource(StrEnum):
    DATABASE = 'database'
    APP_LIST = 'app_list'


# Permission data source
class PermissionSource(StrEnum):
    SYSTEM = "system"
    MENU = "menu"
    CUSTOM = "custom"


# Config model enum
class ConfigCategory(models.TextChoices):
    SITE = 'site', 'Site Information'
    EMAIL = 'email', 'Email Settings'
    EMAIL_TEMPLATE = 'email_template', 'Email Template'
    LINKS = 'links', 'External Links'
    NAV = 'nav', 'Navigation Management'
    TEMPLATE = 'template', 'Template Management'
    SYSTEM = 'system', 'System Settings'
    UPLOAD = 'upload', 'Upload Settings'
    ICONS = 'icons', 'Icons Management'
    LOG = 'log', 'Log Management'
    FILE = 'file', 'File Management'


# Config model enum
class InputType(models.TextChoices):
    TEXT = 'text'
    TEXTAREA = 'textarea'
    IMAGE = 'image'
    SWITCH = 'switch'
    SELECT = 'select'
    RADIO = 'radio'
    CHECKBOX = 'checkbox'
    RICHTEXT = 'richtext'
    PASSWORD = 'password'
    NUMBER = 'number'
    FILE = 'file'


# Navigation type
class TargetChoices(models.TextChoices):
    SELF = '_self', 'Self Window'
    BLANK = '_blank', 'Blank Window'


# Upload file type
class FileType(Enum):
    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'document'
    ARCHIVE = 'archive'


# Upload file mime type
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
