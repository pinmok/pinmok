#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
constants module

Description:
  Global Constants
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin.enums import MimeType, FileType, ErrorCode

# Variable name menus should be defined under in menus.py files
ADMIN_MENU_VAR_NAME = "ADMIN_MENU"

# CMF menus settings variables
ADMIN_MENU_SETTING_KEY = 'CMF_ADMIN_MENU'
MENU_SETTINGS_KEY = 'MENU_IMPORT_PATHS'
PATH_KEY = 'path'
APP_LABEL_KEY = 'app_label'

# Cache keys
ADMIN_ALL_MENU = 'admin_all_menu'
SITE_INFO = 'site_info'
SYS_INFO = 'sys_info'

# Auth menu icon constant
AUTH_ICON = 'tabler-user-shield'

# Custom EmailBackend for overriding email sending configuration
CMF_EMAIL_BACKEND = 'cmfadmin.backends.EmailBackend'

DEFAULT_SORT_ORDER = 10000

# custom sprite.svg file path
CUSTOM_SPRITE_FILE = 'svg/custom_sprite.svg'
CMF_SPRITE_FILE = 'admin/svg/sprite.svg'

UPLOAD_FILE_CONFIG = {
    FileType.IMAGE.value: {
        'size_key': 'upload_image_size',
        'type_key': 'upload_image_type',
        'default_size': 5,
        'default_type': [MimeType.JPEG.value, MimeType.PNG.value, MimeType.GIF.value],
        'mimes': [MimeType.JPEG, MimeType.PNG, MimeType.GIF, MimeType.WEBP, MimeType.BMP, MimeType.SVG, MimeType.AVIF]
    },
    FileType.AUDIO.value: {
        'size_key': 'upload_audio_size',
        'type_key': 'upload_audio_type',
        'default_size': 10,
        'default_type': [MimeType.MP3.value, MimeType.WAV.value],
        'mimes': [MimeType.MP3, MimeType.WAV, MimeType.OGG, MimeType.FLAC, MimeType.AAC, MimeType.OPUS]
    },
    FileType.VIDEO.value: {
        'size_key': 'upload_video_size',
        'type_key': 'upload_video_type',
        'default_size': 20,
        'default_type': [MimeType.MP4.value, MimeType.AVI.value],
        'mimes': [MimeType.MP4, MimeType.WEBM, MimeType.AVI, MimeType.MOV, MimeType.MKV, MimeType.OGV]
    },
    FileType.DOCUMENT.value: {
        'size_key': 'upload_document_size',
        'type_key': 'upload_document_type',
        'default_size': 10,
        'default_type': [MimeType.PDF.value, MimeType.DOCX.value, MimeType.XLSX.value, MimeType.TXT.value],
        'mimes': [MimeType.PDF, MimeType.DOC, MimeType.DOCX, MimeType.XLS, MimeType.XLSX, MimeType.PPT, MimeType.PPTX, MimeType.TXT]
    },
    FileType.ARCHIVE.value: {
        'size_key': 'upload_archive_size',
        'type_key': 'upload_archive_type',
        'default_size': 10,
        'default_type': [MimeType.ZIP.value, MimeType.RAR.value],
        'mimes': [MimeType.ZIP, MimeType.RAR, MimeType.SEVEN_Z, MimeType.TAR, MimeType.GZIP]
    }
}

# Map code → HTTP status
API_HTTP_STATUS = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.SERVER_ERROR: 500,
}

# Default messages
API_DEFAULT_MESSAGES = {
    ErrorCode.SUCCESS: _("Success"),
    ErrorCode.ERROR: _("Error"),
    ErrorCode.BAD_REQUEST: _("Bad request."),
    ErrorCode.VALIDATION_ERROR: _("Validation failed."),
    ErrorCode.NOT_FOUND: _("Resource not found."),
    ErrorCode.PERMISSION_DENIED: _("Permission denied."),
    ErrorCode.SERVER_ERROR: _("Internal server error."),
}
