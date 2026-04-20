#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme module

Description:

Author:
  惠达浪 <crazys@126.com>
Created:
  2026/4/12
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from djangocmf.cmfadmin import widgets
from djangocmf.cmfadmin.datasource import datasource
from djangocmf.cmfadmin.enums import ThemeVarType
from djangocmf.cmfadmin.models import Theme, ThemeTemplate

THEME_CACHE_KEY = 'cmf_active_theme'
THEME_CACHE_TIMEOUT = 3600

# Map ThemeVarType to Django form widget class.
# To add a new type: add the enum value and its widget class here only.
TYPE_WIDGET_MAP = {
    ThemeVarType.TEXT: widgets.CMFTextInput,
    ThemeVarType.TEXTAREA: widgets.CMFTextarea,
    ThemeVarType.NUMBER: widgets.CMFNumberInput,
    ThemeVarType.BOOLEAN: widgets.CMFCheckbox,
}

# Required fields for a var definition in JSON.
_VAR_REQUIRED_FIELDS = ('title', 'type')


@dataclass(kw_only=True)
class ThemeVar:
    """
    Represents a single variable definition declared in a theme config file.

    Each variable maps to a configurable field rendered in the admin interface.
    For datasource variables, the ``source`` field identifies which registered
    datasource to use.
    """
    title: str
    type: ThemeVarType
    default: Any | None = None
    tip: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ThemeVar':
        return cls(
            title=data['title'],
            type=ThemeVarType(data['type']),
            default=data.get('default', None),
            tip=data.get('tip', ''),
            source=data.get('source', ''),
        )


class ThemeServiceError(Exception):
    pass


class ThemeService:
    """
    ThemeService

    Encapsulates theme-related business logic.

    Provides a unified interface for operations related to themes,
    while keeping the underlying implementation flexible and extensible.
    """

    @staticmethod
    def _themes_root() -> Path:
        """Return the themes/ directory found under any configured template DIRS entry."""
        for conf in settings.TEMPLATES:
            for d in conf.get('DIRS', []):
                candidate = Path(d) / 'themes'
                if candidate.is_dir():
                    return candidate
        raise ThemeServiceError(_('No themes directory found in any configured template directory.'))

    @classmethod
    def _theme_dir(cls, directory: str) -> Path:
        return cls._themes_root() / directory

    @classmethod
    def _read_json(cls, path: Path) -> dict:
        """Read and parse a JSON file. Raise ThemeServiceError on failure."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ThemeServiceError(_('Configuration file not found: %(path)s') % {'path': path})
        except json.JSONDecodeError as e:
            raise ThemeServiceError(_('Invalid JSON in %(path)s: %(error)s') % {'path': path, 'error': e})

    @classmethod
    def _invalidate_cache(cls):
        cache.delete(THEME_CACHE_KEY)

    @classmethod
    def _default_value(cls, var: ThemeVar) -> Any:
        """Return a sensible default based on variable type."""
        if var.default is not None:
            return var.default
        if var.type == ThemeVarType.NUMBER:
            return 0
        if var.type == ThemeVarType.BOOLEAN:
            return False
        return ''

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_var(cls, var_def: dict, location: str):
        """
        Validate a single var definition dict.
        Raises ThemeServiceError with a descriptive message on failure.
        ``location`` is a human-readable path string for error messages,
        e.g. 'vars.company_name' or 'fieldsets.sidebar.vars.count'.
        """
        for field in _VAR_REQUIRED_FIELDS:
            if field not in var_def:
                raise ThemeServiceError(
                    _('Missing required field "%(field)s" in %(location)s') % {
                        'field': field,
                        'location': location,
                    }
                )
        try:
            ThemeVarType(var_def['type'])
        except ValueError:
            raise ThemeServiceError(
                _('Unknown type "%(type)s" in %(location)s') % {
                    'type': var_def['type'],
                    'location': location,
                }
            )
        if var_def['type'] == ThemeVarType.DATASOURCE.value and not var_def.get('source'):
            raise ThemeServiceError(
                _('Datasource var at %(location)s must define "source"') % {'location': location}
            )

    @classmethod
    def _validate_config(cls, data: dict, config_file: str):
        """
        Validate all vars and fieldsets in a parsed JSON dict.
        Raises ThemeServiceError on the first problem found.
        ``config_file`` is used in error messages to identify which file failed.
        """
        for key, var_def in data.get('vars', {}).items():
            if not isinstance(var_def, dict):
                raise ThemeServiceError(
                    _('Invalid var definition for "%(key)s" in %(file)s') % {
                        'key': key, 'file': config_file,
                    }
                )
            cls._validate_var(var_def, f'{config_file} > vars.{key}')

        for fs_key, fs_def in data.get('fieldsets', {}).items():
            if not isinstance(fs_def, dict):
                raise ThemeServiceError(
                    _('Invalid fieldset definition for "%(key)s" in %(file)s') % {
                        'key': fs_key, 'file': config_file,
                    }
                )
            if 'title' not in fs_def:
                raise ThemeServiceError(
                    _('Fieldset "%(key)s" in %(file)s is missing "title"') % {
                        'key': fs_key, 'file': config_file,
                    }
                )
            for var_key, var_def in fs_def.get('vars', {}).items():
                if not isinstance(var_def, dict):
                    raise ThemeServiceError(
                        _('Invalid var definition for "%(key)s" in fieldset "%(fs)s" in %(file)s') % {
                            'key': var_key, 'fs': fs_key, 'file': config_file,
                        }
                    )
                cls._validate_var(
                    var_def,
                    f'{config_file} > fieldsets.{fs_key}.vars.{var_key}',
                )

    # ------------------------------------------------------------------
    # Parse config (install-time)
    # ------------------------------------------------------------------

    @classmethod
    def _parse_config(cls, data: dict, config_file: str = '') -> dict:
        """
        Validate and parse vars and fieldsets from a JSON dict.
        Stores the full definition for each var, with 'value' initialised
        from 'default'.  This is the structure persisted to the database.

        Each var entry contains: title, type, default, tip, source, value.
        Each fieldset entry contains: title, and a vars dict of the same shape.
        """
        cls._validate_config(data, config_file or 'config')

        result_vars = {}
        for key, var_def in data.get('vars', {}).items():
            var = ThemeVar.from_dict(var_def)
            entry = var.to_dict()
            entry['value'] = cls._default_value(var)
            result_vars[key] = entry

        result_fieldsets = {}
        for fs_key, fs_def in data.get('fieldsets', {}).items():
            fs_vars = {}
            for var_key, var_def in fs_def.get('vars', {}).items():
                var = ThemeVar.from_dict(var_def)
                entry = var.to_dict()
                entry['value'] = cls._default_value(var)
                fs_vars[var_key] = entry
            result_fieldsets[fs_key] = {
                'title': fs_def['title'],
                'vars': fs_vars,
            }

        return {'vars': result_vars, 'fieldsets': result_fieldsets}

    # ------------------------------------------------------------------
    # Scan Theme
    # ------------------------------------------------------------------

    @classmethod
    def scan(cls) -> list[dict]:
        """
        Scan the themes root directory. Return a list of dicts, one per
        theme package found. Each dict includes an 'installed' flag and,
        if installed, the corresponding Theme pk.
        """
        root = cls._themes_root()
        if not root.exists():
            return []

        installed = {t.directory: t for t in Theme.objects.all()}
        result = []

        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / 'theme.json'
            if not manifest_path.exists():
                continue
            try:
                data = cls._read_json(manifest_path)
            except ThemeServiceError as e:
                result.append({
                    'directory': entry.name,
                    'error': str(e),
                    'installed': False,
                    'is_active': False,
                    'theme_id': None,
                })
                continue

            theme_obj = installed.get(entry.name)
            result.append({
                'directory': entry.name,
                'name': data.get('name', entry.name),
                'version': data.get('version', ''),
                'author': data.get('author', ''),
                'description': data.get('description', ''),
                'preview_url': data.get('preview_url', ''),
                'installed': theme_obj is not None,
                'is_active': theme_obj.is_active if theme_obj else False,
                'theme_id': theme_obj.pk if theme_obj else None,
            })

        return result

    # ------------------------------------------------------------------
    # Install / Uninstall / Reset
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def install(cls, directory: str) -> Theme:
        """
        Install a theme from the given directory name.
        Reads theme.json and all page-level JSON files.
        Raises ThemeServiceError if the directory, theme.json, or any
        page-level JSON fails validation.
        """
        theme_dir = cls._theme_dir(directory)
        if not theme_dir.is_dir():
            raise ThemeServiceError(_('Theme directory not found: %(dir)s') % {'dir': directory})
        if Theme.objects.filter(directory=directory).exists():
            raise ThemeServiceError(_('Theme "%(dir)s" already installed.') % {'dir': directory})

        data = cls._read_json(theme_dir / 'theme.json')

        theme = Theme.objects.create(
            name=data.get('name', directory),
            version=data.get('version', ''),
            author=data.get('author', ''),
            description=data.get('description', ''),
            preview=data.get('preview_url', ''),
            directory=directory,
            config=cls._parse_config(data, 'theme.json'),
        )

        cls._install_templates(theme, theme_dir)
        cls._invalidate_cache()
        return theme

    @classmethod
    def _install_templates(cls, theme: Theme, theme_dir: Path):
        """Scan the theme directory for page-level JSON files and create ThemeTemplate records."""
        for json_file in sorted(theme_dir.glob('*.json')):
            if json_file.name == 'theme.json':
                continue
            try:
                data = cls._read_json(json_file)
            except ThemeServiceError:
                continue

            action = data.get('action', '')
            if not action:
                raise ThemeServiceError(
                    _('Template config %(file)s is missing required field "action"') % {
                        'file': json_file.name,
                    }
                )

            name = data.get('name', '')
            if not name:
                raise ThemeServiceError(
                    _('Template config %(file)s is missing required field "name"') % {
                        'file': json_file.name,
                    }
                )

            filename = json_file.stem  # e.g. 'index' from 'index.json'
            ThemeTemplate.objects.create(
                theme=theme,
                filename=filename,
                name=name,
                action=action,
                order=data.get('order', 0),
                config=cls._parse_config(data, json_file.name),
            )

    @classmethod
    @transaction.atomic
    def uninstall(cls, theme_id: int):
        """Delete a theme and all its templates from the database. Does not touch files."""
        theme = cls._get_theme(theme_id)
        if theme.is_active:
            raise ThemeServiceError(_('Cannot uninstall the active theme.'))
        theme.delete()
        cls._invalidate_cache()

    @classmethod
    @transaction.atomic
    def reset(cls, theme_id: int) -> Theme:
        """
        Re-read the theme JSON files and overwrite all database records.
        User-configured values will be lost.
        """
        theme = cls._get_theme(theme_id)
        directory = theme.directory
        theme.delete()
        result = cls.install(directory)
        cls._invalidate_cache()
        return result

    # ------------------------------------------------------------------
    # Activate
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def activate(cls, theme_id: int):
        """Activate the given theme. Deactivates all others."""
        cls._get_theme(theme_id)
        Theme.objects.all().update(is_active=False)
        Theme.objects.filter(pk=theme_id).update(is_active=True)
        cls._invalidate_cache()

    # ------------------------------------------------------------------
    # Read config (for admin editing)
    # ------------------------------------------------------------------

    @classmethod
    def get_active_theme(cls) -> Optional[Theme]:
        """Return the currently active Theme, or None. Result is cached."""
        cached_pk = cache.get(THEME_CACHE_KEY)
        if cached_pk is not None:
            try:
                return Theme.objects.prefetch_related('templates').get(pk=cached_pk)
            except Theme.DoesNotExist:
                pass

        try:
            theme = Theme.objects.prefetch_related('templates').get(is_active=True)
            cache.set(THEME_CACHE_KEY, theme.pk, THEME_CACHE_TIMEOUT)
            return theme
        except Theme.DoesNotExist:
            return None

    @classmethod
    def get_active_template(cls, action: str) -> Optional[ThemeTemplate]:
        """Return the ThemeTemplate for the active theme that matches the given URL name."""
        theme = cls.get_active_theme()
        if theme is None:
            return None
        try:
            return theme.templates.get(action=action)
        except ThemeTemplate.DoesNotExist:
            return None

    @classmethod
    def get_theme_config(cls, theme_id: int) -> dict:
        """
        Return the stored config dict for a theme, ready for the config editing page.
        The database already holds the full definition + value; no re-merge needed.
        Shape: {'vars': {...}, 'fieldsets': {...}}
        """
        theme = cls._get_theme(theme_id)
        return theme.config

    @classmethod
    def get_template_config(cls, template_id: int) -> dict:
        """
        Return the stored config dict for a page template, ready for the config editing page.
        """
        template = cls._get_template(template_id)
        return template.config

    # ------------------------------------------------------------------
    # Save config
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_submitted_values(config: dict, submitted: dict) -> dict:
        """
        Write submitted POST values into a stored config dict in-place.
        Only the 'value' field of each matching var is updated.
        Unknown keys are silently ignored; definition fields are never touched.
        Returns the mutated config dict.
        """
        for key, value in submitted.get('vars', {}).items():
            if key in config.get('vars', {}):
                config['vars'][key]['value'] = value

        for fs_key, fs_values in submitted.get('fieldsets', {}).items():
            if fs_key in config.get('fieldsets', {}):
                for var_key, value in fs_values.items():
                    if var_key in config['fieldsets'][fs_key].get('vars', {}):
                        config['fieldsets'][fs_key]['vars'][var_key]['value'] = value

        return config

    @classmethod
    def save_config(cls, theme_id: int, submitted: dict):
        """
        Persist user-submitted values for a theme's global config.
        Only the 'value' field of each stored var is updated.
        Definition fields (title, type, tip, source, default) are never touched.
        """
        theme = cls._get_theme(theme_id)
        theme.config = cls._apply_submitted_values(theme.config, submitted)
        theme.save(update_fields=['config'])
        cls._invalidate_cache()

    @classmethod
    def save_template_config(cls, template_id: int, submitted: dict):
        """
        Persist user-submitted values for a page template config.
        Same submitted shape as save_config.
        """
        template = cls._get_template(template_id)
        template.config = cls._apply_submitted_values(template.config, submitted)
        template.save(update_fields=['config'])
        cls._invalidate_cache()

    # ------------------------------------------------------------------
    # Runtime resolution (used by views and template tags)
    # ------------------------------------------------------------------

    @classmethod
    def resolve_template(cls, action: str) -> Optional[str]:
        """
        Return the template file path for the given URL name, relative to
        the Django template loader roots.
        e.g. 'themes/default/index.html'
        Returns None if no active theme or no matching template.
        """
        theme = cls.get_active_theme()
        if theme is None:
            return None
        try:
            template = theme.templates.get(action=action)
        except ThemeTemplate.DoesNotExist:
            return None
        return f'themes/{theme.directory}/{template.filename}.html'

    @classmethod
    def get_vars_context(cls, action: str) -> dict:
        """
        Return a flat dict of variable values for the given action,
        merging global (theme-level) vars and page-level vars.
        Page-level vars override global vars on key collision.
        Used by views to inject variables into the template context.
        """
        theme = cls.get_active_theme()
        if theme is None:
            return {}

        # Extract only the value from each stored var definition
        context = {
            key: var['value']
            for key, var in theme.config.get('vars', {}).items()
        }

        try:
            template = theme.templates.get(action=action)
            context.update({
                key: var['value']
                for key, var in template.config.get('vars', {}).items()
            })
        except ThemeTemplate.DoesNotExist:
            pass

        return context

    @classmethod
    def get_fieldset_context(cls, action: str, fieldset_key: str) -> dict:
        """
        Return a flat dict of variable values for a specific fieldset.
        Used by template tags to inject fieldset variables into rendering context.
        Looks in the page template first, then falls back to the global theme config.
        Returns an empty dict if not found.
        """
        theme = cls.get_active_theme()
        if theme is None:
            return {}

        def _extract_values(config: dict) -> Optional[dict]:
            fs = config.get('fieldsets', {}).get(fieldset_key)
            if not isinstance(fs, dict):
                return None
            return {
                var_key: var['value']
                for var_key, var in fs.get('vars', {}).items()
            }

        # Page-level fieldset takes priority
        try:
            template = theme.templates.get(action=action)
            values = _extract_values(template.config)
            if values is not None:
                return values
        except ThemeTemplate.DoesNotExist:
            pass

        # Fall back to global fieldset
        return _extract_values(theme.config) or {}

    # ------------------------------------------------------------------
    # Config context for admin editing page
    # ------------------------------------------------------------------

    @classmethod
    def get_config_context(cls, theme_id: int, template_id: int | None) -> dict:
        """
        Return all data needed for the config editing page.

        config_data contains two lists ready for template iteration:
        - vars: list of field dicts (key, title, tip, widget, value)
        - fieldsets: list of group dicts (key, title, fields), where each
          fields entry has the same shape as a vars field dict.
        """
        theme = cls._get_theme(theme_id)
        templates = ThemeTemplate.objects.filter(theme=theme).order_by('order', 'name')

        if template_id:
            current_template = cls._get_template(template_id)
            raw_config = cls.get_template_config(template_id)
        else:
            current_template = None
            raw_config = cls.get_theme_config(theme_id)

        config_data = cls._build_config_context(raw_config)

        return {
            'theme': theme,
            'templates': templates,
            'current_template': current_template,
            'config_data': config_data,
        }

    @classmethod
    def _render_var(cls, key: str, var_data: dict, fs_key: str = '') -> dict:
        """
        Convert a single stored var dict into a template-friendly field dict.
        Resolves the widget instance so the template never needs to inspect type.
        """
        var = ThemeVar.from_dict(var_data)
        value = var_data.get('value', cls._default_value(var))
        name = f'fieldset__{fs_key}__{key}' if fs_key else f'var__{key}'
        widget = cls.get_widget_for_var(var)
        html = widget.render(name, value) if widget else ''

        return {
            'key': key,
            'title': var.title,
            'tip': var.tip,
            'html': html,
            'value': var_data.get('value', cls._default_value(var)),
        }

    @classmethod
    def _build_config_context(cls, raw_config: dict) -> dict:
        """
        Convert the raw stored config dict into a template-friendly structure.
        Resolves widget instances for each var so the template can call
        widget.render() without knowing the type.
        """
        rendered_vars = [
            cls._render_var(key, var_data)
            for key, var_data in raw_config.get('vars', {}).items()
        ]

        rendered_fieldsets = []
        for fs_key, fs_data in raw_config.get('fieldsets', {}).items():
            fields = [
                cls._render_var(var_key, var_data, fs_key)
                for var_key, var_data in fs_data.get('vars', {}).items()
            ]
            rendered_fieldsets.append({
                'key': fs_key,
                'title': fs_data.get('title', fs_key),
                'fields': fields,
            })

        return {
            'vars': rendered_vars,
            'fieldsets': rendered_fieldsets,
        }

    # ------------------------------------------------------------------
    # Private getters
    # ------------------------------------------------------------------

    @staticmethod
    def _get_theme(theme_id: int) -> Theme:
        try:
            return Theme.objects.get(pk=theme_id)
        except Theme.DoesNotExist:
            raise ThemeServiceError(_('Theme not found.'))

    @staticmethod
    def _get_template(template_id: int) -> ThemeTemplate:
        try:
            return ThemeTemplate.objects.select_related('theme').get(pk=template_id)
        except ThemeTemplate.DoesNotExist:
            raise ThemeServiceError(_('Theme template not found.'))

    @staticmethod
    def get_widget_for_var(var: ThemeVar):
        """
        Given a ThemeVar instance, return the appropriate Widget instance,
        or None if the type is unknown or datasource is not registered.
        To support a new type, add it to TYPE_WIDGET_MAP only.
        """
        if var.type == ThemeVarType.DATASOURCE:
            widget_class = datasource.get(var.source)
            return widget_class() if widget_class else None

        widget_class = TYPE_WIDGET_MAP.get(var.type)
        return widget_class() if widget_class else None  # type: ignore
