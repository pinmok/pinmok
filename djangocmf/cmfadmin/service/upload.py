#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload service module

Description:
  Provides UploadValidator and UploadService for handling file uploads.
  UploadValidator reads allowed types and size limits from ConfigService.
  UploadService orchestrates validation and storage via the Upload utility.

  When file_type is None, all configured file types are accepted and the
  largest configured size limit is used. This mode is intended for the
  Resource admin upload form where the type is not known in advance.
Author:
  惠达浪 <crazys@126.com>
Created:
  2026-03-12
"""
import io
from datetime import datetime
from pathlib import Path

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
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

    When file_type is None, all configured types are merged and the largest
    size limit across all types is used.

    Does not touch storage or the database.
    """

    def __init__(self, file_type: FileType | None):
        self.file_type = file_type
        self._allowed_mimes, self._max_size = self._load_config()

    def _load_config(self) -> tuple[list[str], int]:
        """
        Load allowed MIME types and max size from ConfigService.
        When file_type is None, merge all types and use the largest size limit.
        """
        if self.file_type is not None:
            return self._load_single_type(self.file_type)

        # All-types mode: union of all MIME lists, max of all size limits
        all_mimes: set[str] = set()
        max_size = 0
        for ft in _FILE_TYPE_CONFIG_KEYS:
            mimes, size = self._load_single_type(ft)
            all_mimes.update(mimes)
            max_size = max(max_size, size)
        return list(all_mimes), max_size

    @staticmethod
    def _load_single_type(file_type: FileType) -> tuple[list[str], int]:
        """Load allowed MIME types and max size for a single FileType."""
        keys = _FILE_TYPE_CONFIG_KEYS[file_type]

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

    def get_accepted_mimes(self) -> list[str]:
        """
        Return the list of allowed MIME types.
        Used by the upload form to populate the <input accept> attribute.
        """
        return list(self._allowed_mimes)


class UploadService:
    """
    Orchestrates file upload: validation, storage, and database persistence.

    Responsibilities:
      - Detect real MIME type via Upload utility
      - Validate against configured rules via UploadValidator
      - Delegate storage to Upload utility
      - Deduplicate by SHA-256 hash via Resource table
      - Return Resource instance to the caller

    When file_type is None, all configured file types are accepted. The actual
    FileType written to the Resource record is inferred from the detected MIME.
    """

    def __init__(
            self,
            file_type: FileType | None,
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

    @staticmethod
    def _infer_file_type(detected_mime: str):
        """
        Infer FileType value from a detected MIME type.
        Falls back to empty string if no match is found.
        Used when the service is initialized in all-types mode (file_type=None).
        """
        mime_lower = detected_mime.lower()
        if mime_lower.startswith('image/'):
            return FileType.IMAGE.value
        if mime_lower.startswith('audio/'):
            return FileType.AUDIO.value
        if mime_lower.startswith('video/'):
            return FileType.VIDEO.value
        if mime_lower in ('application/pdf',):
            return FileType.DOCUMENT.value
        if mime_lower in (
                'application/zip',
                'application/x-rar-compressed',
                'application/x-7z-compressed',
                'application/x-tar',
                'application/gzip',
        ):
            return FileType.ARCHIVE.value
        return ''

    @staticmethod
    def _compress_image(file: UploadedFile) -> UploadedFile:
        """
        Re-compress image using Pillow to reduce file size.
        PNG with transparency is kept as PNG with optimize=True.
        Everything else is converted to JPEG at quality=85.
        """
        img = Image.open(file)
        output = io.BytesIO()

        has_transparency = img.mode in ('RGBA', 'LA') or (
                img.mode == 'P' and 'transparency' in img.info
        )

        if has_transparency:
            img.save(output, format='PNG', optimize=True)
            content_type = 'image/png'
            ext = '.png'
        else:
            img = img.convert('RGB')
            img.save(output, format='JPEG', quality=85, optimize=True)
            content_type = 'image/jpeg'
            ext = '.jpg'

        output.seek(0)
        new_name = Path(file.name).stem + ext
        return InMemoryUploadedFile(
            output, 'file', new_name, content_type, output.getbuffer().nbytes, None
        )

    def get_accepted_mimes(self) -> list[str]:
        """
        Return the list of allowed MIME types for this service instance.
        Delegates to the validator. Used to populate <input accept>.
        """
        return self._validator.get_accepted_mimes()

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

        if self.file_type == FileType.IMAGE:
            file = self._compress_image(file)

        # Calculate file hash and check if a resource with the same hash already exists (deduplication).
        file_hash = self._uploader.calculate_hash(file)
        existing_resource = Resource.objects.filter(hash=file_hash).first()
        if existing_resource:
            return existing_resource

        # Persist file to storage
        result: UploadResult = self._uploader.save(file)

        # Resolve uploaded_by — AnonymousUser is treated as None
        uploaded_by = self.user if (self.user and self.user.is_authenticated) else None

        # Resolve file_type: use configured value or infer from MIME in all-types mode
        file_type_value = (
            self.file_type.value
            if self.file_type is not None
            else self._infer_file_type(detected_mime)
        )

        # Deduplicate by hash, create if not exists
        resource, _ = Resource.objects.get_or_create(
            hash=result.hash,
            defaults={
                'url': result.path,
                'original_name': result.original_name,
                'size': result.size,
                'file_type': file_type_value,
                'mime_type': detected_mime,
                'uploaded_by': uploaded_by,
            }
        )

        return resource
