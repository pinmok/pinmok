#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload module

Description:
  Service of upload file
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-26
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from cmfadmin.constants import UPLOAD_FILE_CONFIG
from cmfadmin.enums import FileType
from cmfadmin.libs.upload import Upload, UploadResult
from cmfadmin.models import UploadFile
from cmfadmin.service.config import ConfigService
from cmfadmin.utils.tools import int_to_bytes


class UploadService:
    def __init__(self, use_unique_name: bool = True):
        self.use_unique_name = use_unique_name

    @staticmethod
    def _get_config(file_type: FileType) -> dict:
        """
        Get resolved config for a file type, including allowed allowed_mimes, size and mimes.
        Priority: ConfigService -> Default config.
        """
        cfg = UPLOAD_FILE_CONFIG[file_type.value]

        # Allowed MIME types (from user config or default)
        allowed_mimes = ConfigService.get(cfg['type_key'], default=cfg['default_type'])
        if isinstance(allowed_mimes, str):
            allowed_mimes = [e.strip().lower() for e in allowed_mimes.split(',') if e.strip()]
        else:
            allowed_mimes = [e.strip().lower() for e in allowed_mimes if e.strip()]

        # Max size
        max_size_mb = int(ConfigService.get(cfg['size_key'], default=cfg['default_size']))
        max_size = max_size_mb * 1024 * 1024

        return {
            "allowed_mimes": allowed_mimes,
            "max_size": max_size,
        }

    @staticmethod
    def _validate_mime(mime: str, allowed_mimes: list[str]) -> None:
        if mime not in allowed_mimes:
            raise ValidationError(f"MIME type {mime} is not allowed.")

    @staticmethod
    def _validate_size(size: int, max_size: int) -> None:
        if size > max_size:
            raise ValidationError(f"File size exceeds limit ({int_to_bytes(max_size)}).")

    def _validate(self, file: UploadedFile, file_type: FileType) -> bool:
        """
        Validate file extension, MIME type and size based on config.
        """
        cfg = self._get_config(file_type)
        mime = file.content_type.lower()
        size = file.size

        self._validate_mime(mime, cfg["allowed_mimes"])
        self._validate_size(size, cfg["max_size"])
        return True

    def save(self, file: UploadedFile, file_type: FileType, user=None) -> UploadResult:
        """
        Validate and save the file using the Upload utility.
        Returns an UploadResult object with path, url, hash, etc.
        """
        self._validate(file, file_type)

        file.seek(0)
        file_hash = Upload.calculate_hash(file)
        existing = UploadFile.objects.filter(hash=file_hash).first()
        if existing:
            return existing.to_result()

        file.seek(0)
        uploader = Upload(use_unique_name=self.use_unique_name)
        file_info = uploader.save(file, file_hash)

        # Save file info to DB
        UploadFile.create_from_result(file_info, user)

        return file_info

    @staticmethod
    def delete(file_path: str) -> bool:
        """
        Delete uploaded file (both file and DB record) by file path.
        Returns True if deleted, False if not found.
        """
        try:
            file = UploadFile.objects.get(path=file_path)
        except UploadFile.DoesNotExist:
            return False

        # Delete DB record
        deleted_count, _ = file.delete()
        if deleted_count:
            Upload.delete(file_path)
            return True
        return False
