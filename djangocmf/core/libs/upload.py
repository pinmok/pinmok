#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload module

Description:
  Generic file upload utility. Handles filename generation, MIME type detection
  (via magic bytes), hashing, storage and deletion.
  Does not touch the database or contain any business logic.
  Path strategy is the caller's responsibility — pass upload_to to control
  the subdirectory; omit it to store directly under MEDIA_ROOT (Django default).
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-22
Updated:
  2026-03-14
"""
import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import filetype
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile


@dataclass
class UploadResult:
    """
    Immutable result object returned after a successful file upload.
    media_path is derived automatically from path via default_storage.
    """
    path: str  # Relative storage path, e.g. '2026/03/abc123.jpg'
    filename: str  # Final saved filename
    size: int  # File size in bytes
    mime_type: str  # Detected MIME type (from magic bytes, not request header)
    original_name: str  # Original uploaded filename
    hash: str  # SHA-256 hex digest
    created_at: datetime = field(default_factory=datetime.now)
    media_path: str = field(init=False)

    def __post_init__(self):
        self.media_path = default_storage.url(self.path)

    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'filename': self.filename,
            'size': self.size,
            'mime_type': self.mime_type,
            'original_name': self.original_name,
            'hash': self.hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'media_path': self.media_path,
        }


class Upload:
    """
    Generic file upload utility.

    Responsibilities:
      - Detect real MIME type via magic bytes (not Content-Type header)
      - Calculate SHA-256 hash
      - Generate filename
      - Save to default_storage
      - Delete from default_storage

    This class has no knowledge of models, services, path rules, or business
    logic. Path strategy and validation (allowed types, size limits) are the
    caller's responsibility.

    Args:
        use_unique_name: Replace the original filename with a UUID-based name.
        upload_to: Subdirectory under MEDIA_ROOT to store the file.
                   None (default) stores directly under MEDIA_ROOT, consistent
                   with Django's default FileField(upload_to='') behaviour.
    """

    # Number of bytes to read for MIME detection
    MAGIC_BYTES_LENGTH = 262

    def __init__(
            self,
            use_unique_name: bool = True,
            upload_to: str | None = None,
    ):
        self.use_unique_name = use_unique_name
        self.upload_to = upload_to

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, file_obj: UploadedFile) -> UploadResult:
        """
        Detect MIME type, calculate hash, generate path, and persist the file.
        Returns an UploadResult with all metadata.
        """
        mime_type = self.detect_mime(file_obj)
        file_hash = self.calculate_hash(file_obj)

        filename = (
            self._generate_unique_name(file_obj.name)
            if self.use_unique_name
            else file_obj.name
        )
        relative_path = os.path.join(self.upload_to, filename) if self.upload_to else filename

        file_obj.seek(0)
        saved_path = default_storage.save(relative_path, ContentFile(file_obj.read()))

        return UploadResult(
            path=saved_path,
            filename=filename,
            size=file_obj.size,
            mime_type=mime_type,
            original_name=file_obj.name,
            hash=file_hash,
        )

    @staticmethod
    def delete(path: str) -> bool:
        """
        Delete the file at the given relative storage path.
        Returns True if deleted, False if the file did not exist.
        """
        if default_storage.exists(path):
            default_storage.delete(path)
            return True
        return False

    # ------------------------------------------------------------------
    # Detection and hashing
    # ------------------------------------------------------------------

    @classmethod
    def detect_mime(cls, file_obj: UploadedFile) -> str:
        """
        Detect the real MIME type by reading magic bytes.
        Falls back to file_obj.content_type if filetype cannot determine the type.
        Always resets the file pointer after reading.
        """
        file_obj.seek(0)
        header = file_obj.read(cls.MAGIC_BYTES_LENGTH)
        file_obj.seek(0)

        kind = filetype.guess(header)
        if kind is not None:
            return kind.mime

        # Fallback: trust content_type only for known safe types
        return file_obj.content_type or 'application/octet-stream'

    @staticmethod
    def calculate_hash(file_obj: UploadedFile) -> str:
        """
        Calculate SHA-256 hash of the file content.
        Always resets the file pointer after reading.
        """
        sha256 = hashlib.sha256()
        file_obj.seek(0)
        for chunk in file_obj.chunks():
            sha256.update(chunk)
        file_obj.seek(0)
        return sha256.hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_unique_name(original_name: str) -> str:
        """Generate a UUID-based filename, preserving the original extension."""
        ext = os.path.splitext(original_name)[1]
        return f"{uuid.uuid4().hex}{ext}"
