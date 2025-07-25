#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload module

Description:
  
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-07-22
"""
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _


class UploadPathRule(StrEnum):
    MONTH = 'month'
    DATE = 'date'
    COUNT = 'count'
    CUSTOM = 'custom'

    @property
    def label(self) -> str:
        return {
            self.DATE: 'By Date: YYYY/MM/DD — For frequent uploads',
            self.MONTH: 'By Month: YYYY/MM — For blogs or infrequent uploads',
            self.COUNT: 'By Count: 1000 files/folder — For large datasets',
            self.CUSTOM: 'Custom: Reserved for advanced rules',
        }[self]


@dataclass
class UploadResult:
    path: str  # Relative path, e.g., '2025/07/22/file.png'
    filename: str  # Final saved filename
    size: int  # File size in bytes
    mime_type: str  # MIME type of the file
    original_name: str  # Original uploaded filename
    hash: str | None = None  # Optional: hash for deduplication or reference


class UploadValidator:
    def __init__(self, max_size: int | None = None, allowed_types: list[str] | None = None):
        self.allowed_types = allowed_types or []
        self.max_size = max_size or 5 * 1024 * 1024  # default 10MB

    def validate(self, file_obj: UploadedFile) -> None:
        if file_obj.size > self.max_size:
            raise ValueError(_('File size exceeds limit'))

        if self.allowed_types and file_obj.content_type not in self.allowed_types:
            raise ValueError(_('File type not allowed'))


# Core upload service
class UploadService:
    def __init__(self, base_dir: str, validator: UploadValidator | None = None):
        self.base_dir = base_dir.rstrip('/')
        self.validator = validator or UploadValidator()

    @staticmethod
    def _calculate_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _generate_path(self, filename: str, rule: UploadPathRule, custom_path: str | None = None) -> str:
        today = datetime.today()
        match rule:
            case UploadPathRule.DATE:
                subdir = today.strftime('%Y/%m/%d')
            case UploadPathRule.MONTH:
                subdir = today.strftime('%Y/%m')
            case UploadPathRule.COUNT:
                subdir = self.count_based_dir()
            case UploadPathRule.CUSTOM:
                if not custom_path:
                    raise ValueError('Custom path rule requires a path')
                subdir = custom_path.strip('/')
            case _:
                raise ValueError('Invalid upload rule')
        return os.path.join(subdir, filename)

    def save(self, file_obj: UploadedFile, rule: UploadPathRule, custom_path: str | None = None) -> UploadResult:
        self.validator.validate(file_obj)
        rel_path = self._generate_path(file_obj.name, rule, custom_path)
        full_path = os.path.join(self.base_dir, rel_path)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        return UploadResult(
            path=rel_path,
            filename=os.path.basename(full_path),
            size=file_obj.size,
            mime_type=file_obj.content_type,
            original_name=file_obj.name,
            hash=self._calculate_hash(full_path)
        )

    @staticmethod
    def count_based_dir() -> str:
        # You can replace this logic with actual folder scanning if needed
        # For now, just return a placeholder folder like 'bucket_001'
        return 'bucket_001'
