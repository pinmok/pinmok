#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload service module

Description:
  Provides UploadValidator and UploadService for handling file uploads.
  UploadValidator reads allowed types and size limits from ConfigService.
  UploadService orchestrates validation and storage via the Upload utility.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026-03-12
"""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin.enums import FileType, UploadConfigKey, ConfigCategory, UploadPathRule
from djangocmf.cmfadmin.models import Resource
from djangocmf.cmfadmin.service.config import ConfigService
from djangocmf.core.libs.upload import Upload, UploadResult

# Maps FileType to its corresponding ConfigService keys
_FILE_TYPE_CONFIG_KEYS = {
    FileType.IMAGE: {
        'size_key': UploadConfigKey.IMAGE_SIZE,
        'type_key': UploadConfigKey.IMAGE_TYPE,
    },
    FileType.AUDIO: {
        'size_key': UploadConfigKey.AUDIO_SIZE,
        'type_key': UploadConfigKey.AUDIO_TYPE,
    },
    FileType.VIDEO: {
        'size_key': UploadConfigKey.VIDEO_SIZE,
        'type_key': UploadConfigKey.VIDEO_TYPE,
    },
    FileType.DOCUMENT: {
        'size_key': UploadConfigKey.DOCUMENT_SIZE,
        'type_key': UploadConfigKey.DOCUMENT_TYPE,
    },
    FileType.ARCHIVE: {
        'size_key': UploadConfigKey.ARCHIVE_SIZE,
        'type_key': UploadConfigKey.ARCHIVE_TYPE,
    },
}


class UploadValidator:
    """
    Validates an uploaded file against configured rules.

    Reads allowed MIME types and max file size from ConfigService.
    ConfigService falls back to schema defaults if no DB value is set.

    Does not touch storage or the database.
    """

    def __init__(self, file_type: FileType):
        self.file_type = file_type
        self._allowed_mimes, self._max_size = self._load_config()

    def _load_config(self) -> tuple[list[str], int]:
        """Load allowed MIME types and max size from ConfigService."""
        keys = _FILE_TYPE_CONFIG_KEYS[self.file_type]

        # Allowed MIME types — stored as comma-separated string in DB
        raw = ConfigService.get(ConfigCategory.UPLOAD, keys['type_key'])
        if isinstance(raw, str):
            allowed_mimes = [m.strip().lower() for m in raw.split(',') if m.strip()]
        elif isinstance(raw, (list, tuple)):
            allowed_mimes = [m.strip().lower() for m in raw if m.strip()]
        else:
            allowed_mimes = []

        # Max size — stored as integer (MB), convert to bytes
        max_size_mb = int(ConfigService.get(ConfigCategory.UPLOAD, keys['size_key']))
        max_size = max_size_mb * 1024 * 1024

        return allowed_mimes, max_size

    def validate(self, file: UploadedFile, detected_mime: str) -> None:
        """
        Validate MIME type and file size.
        Raises ValidationError if validation fails.
        Uses detected_mime (from magic bytes) instead of content_type.
        """
        self._validate_mime(detected_mime)
        self._validate_size(file.size)

    def _validate_mime(self, detected_mime: str) -> None:
        if detected_mime not in self._allowed_mimes:
            raise ValidationError(
                _("File type '%(mime)s' is not allowed.") % {'mime': detected_mime}
            )

    def _validate_size(self, size: int) -> None:
        if size > self._max_size:
            max_mb = self._max_size // (1024 * 1024)
            raise ValidationError(
                _("File size exceeds the %(limit)s MB limit.") % {'limit': max_mb}
            )


class UploadService:
    """
    Orchestrates file upload: validation, storage, and database persistence.

    Responsibilities:
      - Detect real MIME type via Upload utility
      - Validate against configured rules via UploadValidator
      - Delegate storage to Upload utility
      - Deduplicate by SHA-256 hash via Resource table
      - Return Resource instance to the caller
    """

    def __init__(
            self,
            file_type: FileType,
            use_unique_name: bool = True,
            upload_to: str | None = None,
            user=None
    ):
        self.file_type = file_type
        self.user = user
        upload_to = self._resolve_upload_to(upload_to)
        self._uploader = Upload(use_unique_name=use_unique_name, upload_to=upload_to)
        self._validator = UploadValidator(file_type)

    @staticmethod
    def _resolve_upload_to(override: str | None = None) -> str:
        """
        Resolve the upload subdirectory.

        If override is provided, it is used directly.
        Otherwise, the path is derived from the configured UploadPathRule.
        """
        if override is not None:
            return override

        rule = ConfigService.get(ConfigCategory.UPLOAD, UploadConfigKey.UPLOAD_PATH_RULE)
        today = datetime.today()
        match rule:
            case UploadPathRule.DATE:
                return today.strftime('%Y/%m/%d')
            case UploadPathRule.MONTH:
                return today.strftime('%Y/%m')
            case _:
                return today.strftime('%Y/%m')

    def save(self, file: UploadedFile) -> Resource:
        """
        Detect MIME type, validate, save file, and persist to database.
        Deduplicates by SHA-256 hash — returns existing Resource if hash matches.
        Returns Resource instance on success.
        Raises ValidationError if validation fails.
        """

        # Detect real MIME type from magic bytes before validation
        detected_mime = Upload.detect_mime(file)

        # Validate type and size against config
        self._validator.validate(file, detected_mime)

        # Persist file to storage
        result: UploadResult = self._uploader.save(file)

        # Resolve uploaded_by — AnonymousUser is treated as None
        uploaded_by = self.user if (self.user and self.user.is_authenticated) else None

        # Deduplicate by hash, create if not exists
        resource, _ = Resource.objects.get_or_create(
            hash=result.hash,
            defaults={
                'url': result.path,
                'original_name': result.original_name,
                'size': result.size,
                'file_type': self.file_type.value,
                'mime_type': detected_mime,
                'uploaded_by': uploaded_by,
            }
        )

        return resource
