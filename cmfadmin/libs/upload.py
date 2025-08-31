#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload module

Description:
  Handles saving files to disk and returns metadata.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-22
"""
import hashlib
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import StrEnum

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from cmfadmin.templatetags.media import media_url


class UploadPathRule(StrEnum):
    """Defines strategies for organizing uploaded files"""
    MONTH = 'month'
    DATE = 'date'
    COUNT = 'count'
    CUSTOM = 'custom'

    @property
    def label(self):
        return {
            self.DATE: _('By Date: YYYY/MM/DD — For frequent uploads'),
            self.MONTH: _('By Month: YYYY/MM — For blogs or infrequent uploads'),
            self.COUNT: _('By Count: 1000 files/folder — For large datasets'),
            self.CUSTOM: _('Custom: Reserved for advanced rules'),
        }[self]


@dataclass
class UploadResult:
    """Result object returned after successful file upload"""
    path: str  # Relative path, e.g., '2025/07/22/file.png'
    filename: str  # Final saved filename
    size: int  # File size in bytes
    mime_type: str  # MIME type of the file
    original_name: str  # Original uploaded filename
    hash: str | None = None  # Optional: hash for deduplication or reference
    media_path: str = field(init=False)

    def __post_init__(self):
        self.media_path = media_url(self.path)

    def to_dict(self) -> dict:
        return asdict(self)


class Upload:
    """Core upload utility"""

    def __init__(
            self,
            rule: UploadPathRule = UploadPathRule.MONTH,
            use_unique_name: bool = True,
            custom_path: str | None = None
    ):
        self.rule = rule
        self.use_unique_name = use_unique_name
        self.custom_path = custom_path

    @staticmethod
    def calculate_hash(file_obj: UploadedFile) -> str:
        """Calculate SHA256 hash directly from uploaded file content"""
        sha256 = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _count_based_dir() -> str:
        """Stub for count-based directory naming"""
        # TODO 目录名生成逻辑
        # 1、每个目录下存放的文件数
        # 2、目录名规则
        return 'bucket_001'

    @staticmethod
    def _generate_unique_name(original_name: str) -> str:
        """Generate a unique filename using UUID, preserving the file extension."""
        ext = os.path.splitext(original_name)[1]
        return f"{uuid.uuid4().hex}{ext}"

    def _generate_subdir(self) -> str:
        """Generate relative directory path based on rule"""
        today = datetime.today()

        match self.rule:
            case UploadPathRule.DATE:
                return today.strftime('%Y/%m/%d')
            case UploadPathRule.MONTH:
                return today.strftime('%Y/%m')
            case UploadPathRule.COUNT:
                return self._count_based_dir()
            case UploadPathRule.CUSTOM:
                if not self.custom_path:
                    raise ValueError(_('Custom path rule requires a path'))
                return self.custom_path.strip('/')

    def save(self, file_obj: UploadedFile, file_hash: str) -> UploadResult:
        """Save file to disk and return file metadata"""
        filename = self._generate_unique_name(file_obj.name) if self.use_unique_name else file_obj.name
        subdir = self._generate_subdir()
        relative_path = os.path.join(subdir, filename)

        file_obj.seek(0)  # Ensure pointer is reset before saving
        saved_path = default_storage.save(relative_path, ContentFile(file_obj.read()))

        return UploadResult(
            path=saved_path,
            filename=filename,
            size=file_obj.size,
            mime_type=file_obj.content_type,
            original_name=file_obj.name,
            hash=file_hash
        )

    @staticmethod
    def delete(path: str) -> bool:
        """Delete the file at the given relative path"""
        if default_storage.exists(path):
            default_storage.delete(path)
            return True
        return False
