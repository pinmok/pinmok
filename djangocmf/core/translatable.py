#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translatable module

Description:
  Generic transparent translation layer for djangocmf.

  Usage contract:
    - Main table inherits TranslatableModel
    - Translation table inherits TranslationModel
    - Translation table FK related_name must be 'translations'
    - Translation table language field must be 'language'

Author:
  惠达浪 <crazys@126.com>
Created:
  2026/5/8
"""
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _

from djangocmf.core.constants import TRANSLATION_RELATED_NAME


class TranslatableModel(models.Model):
    """
    Abstract base for models that have a paired translation table.

    The paired translation table must have:
      - A FK to this model with related_name='translations'
      - A 'language' field

    Access translated fields via:
      obj.translation.name      (current language, with fallback)
      obj.get_translation('en') (explicit language)
    """

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # Core translation access
    # ------------------------------------------------------------------

    def _get_cached_translations(self):
        """
        Return prefetched translations if available, otherwise hit the DB
        and cache the result on the instance for the lifetime of this object.
        """
        # Respect Django's prefetch_related cache (set by with_translations())
        prefetch_cache = self.__dict__.get('_prefetched_objects_cache', {})
        if 'translations' in prefetch_cache:
            return list(prefetch_cache['translations'])

        # Fall back to per-instance cache to avoid repeated queries
        if not hasattr(self, '_translation_cache'):
            manager = getattr(self, TRANSLATION_RELATED_NAME, None)
            if manager is None:
                raise AttributeError(
                    f'{self.__class__.__name__} must define related_name="translations"'
                )
            self._translation_cache = list(manager.all())
        return self._translation_cache

    def get_translation(self, language=None) -> Optional["TranslationModel"]:
        """
        Return the translation object for the given language.
        Falls back to the first available translation if the requested
        language is not found.

        Returns None if no translations exist at all.
        """
        lang = language or get_language() or settings.LANGUAGE_CODE
        # Normalize: Django sometimes returns 'zh-hans', strip to base code
        # only when an exact match fails (see fallback logic below)
        translations = self._get_cached_translations()

        if not translations:
            return None

        # 1. Exact match
        for t in translations:
            if t.language == lang:
                return t

        # 2. Base-language match (e.g. 'zh-hans' -> 'zh')
        base_lang = lang.split('-')[0]
        for t in translations:
            if t.language.split('-')[0] == base_lang:
                return t

        # 3. Default language defined in settings
        default_lang = settings.LANGUAGE_CODE
        for t in translations:
            if t.language == default_lang:
                return t

        # 4. Last resort: first available translation
        return translations[0]

    @property
    def translation(self):
        """
        Shortcut property for templates and serializers:
            {{ obj.translation.name }}
        """
        return self.get_translation()

    # ------------------------------------------------------------------
    # Bulk prefetch helper (resolves N+1)
    # ------------------------------------------------------------------

    @classmethod
    def with_translations(cls, queryset=None):
        """
        Return a queryset with translations prefetched.

        Usage:
            Category.with_translations()
            Category.with_translations(Category.objects.filter(is_active=True))

        The prefetched data is used automatically by get_translation() /
        the translation property, so no extra code is needed in templates
        or serializers.
        """
        qs = queryset if queryset is not None else cls.objects.all()
        return qs.prefetch_related(TRANSLATION_RELATED_NAME)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def invalidate_translation_cache(self):
        """Force a fresh DB read on next access (call after saving a translation)."""
        if hasattr(self, '_translation_cache'):
            del self._translation_cache

    def __str__(self):
        t = self.get_translation()
        if t is None:
            return f'{self.__class__.__name__} [{self.pk}]'

        display = getattr(t, 'get_display_text', None)
        if display is None:
            return str(t)

        return display()


class TranslationModel(models.Model):
    """
    Abstract base for translation tables.

    Subclasses must define:
      - A FK to the main model with related_name='translations'
        (recommended: import and use constant TRANSLATION_RELATED_NAME, e.g.
        from djangocmf.core.constants import TRANSLATION_RELATED_NAME
        instead of hardcoding the string)
      - constraints = [
            models.UniqueConstraint(
                fields=['<fk_field_name>', 'language'],
                name='uniq_<fk_field_name>_language'
            )
        ]

    Example:
        class CategoryTranslation(TranslationModel):
            category = models.ForeignKey(
                Category,
                on_delete=models.CASCADE,
                related_name='translations'
            )
            name = models.CharField(max_length=255)
            description = models.CharField(max_length=200, blank=True, default='')

            class Meta(TranslationModel.Meta):
                constraints = [
                    models.UniqueConstraint(
                        fields=['category', 'language'],
                        name='uniq_category_language'
                    )
                ]
    """
    language = models.CharField(
        _('language'),
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
        db_index=True,
        help_text=_('Which language this translation belongs to.')
    )

    class Meta:
        abstract = True

    def get_display_text(self):
        raise NotImplementedError

    def __str__(self):
        return f'[{self.language}] {self.get_display_text()}'
