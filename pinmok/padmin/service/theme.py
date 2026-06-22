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
import inspect
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _, get_language

from pinmok.core.constants import DEFAULT_SORT_ORDER
from pinmok.core.utils.helper import get_valid_app_labels
from pinmok.padmin import widgets
from pinmok.padmin.datasource import datasource
from pinmok.padmin.enums import ThemeVarType
from pinmok.padmin.models import Theme, ThemeTemplate

THEME_CACHE_KEY = 'pinmok_active_theme'
THEME_CACHE_TIMEOUT = 3600
THEME_CACHE_APP_LABELS_KEY = 'pinmok_theme_app_labels'
THEMES_DIR_NAME = 'themes'

# Map ThemeVarType to Django form widget class.
# To add a new type: add the enum value and its widget class here only.
TYPE_WIDGET_MAP = {
    ThemeVarType.TEXT: widgets.PinmokTextInput,
    ThemeVarType.TEXTAREA: widgets.PinmokTextarea,
    ThemeVarType.NUMBER: widgets.PinmokNumberInput,
    ThemeVarType.BOOLEAN: widgets.PinmokSwitch,
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
    options: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ThemeVar':
        """
        Base fields are handled explicitly; everything else goes into options.
        This handles two cases:
        1. Raw JSON definition: extra fields like 'source', 'multiple' are written
           directly at the top level and collected into options via `extra`.
        2. Database-stored structure: options are already nested under 'options'
           key (produced by to_dict()), collected via `stored_options`.
        Both are merged so from_dict works regardless of the source.
        """
        base_key = {'title', 'type', 'default', 'tip'}
        stored_options = data.get('options', {})
        extra = {k: v for k, v in data.items() if k not in base_key and k != 'options'}
        return cls(
            title=data['title'],
            type=ThemeVarType(data['type']),
            default=data.get('default', None),
            tip=data.get('tip', ''),
            options={**stored_options, **extra},
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
                candidate = Path(d) / THEMES_DIR_NAME
                if candidate.is_dir():
                    return candidate
        raise ThemeServiceError(_('No themes directory found in any configured template directory.'))

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
    def _invalidate_cache(cls, app_label: str | None = None):
        if app_label:
            cache.delete(f'{THEME_CACHE_KEY}:{app_label}')
        else:
            app_labels = cache.get(THEME_CACHE_APP_LABELS_KEY) or []
            for label in app_labels:
                cache.delete(f'{THEME_CACHE_KEY}:{label}')
            cache.delete(THEME_CACHE_APP_LABELS_KEY)

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
        for f in _VAR_REQUIRED_FIELDS:
            if f not in var_def:
                raise ThemeServiceError(
                    _('Missing required field "%(field)s" in %(location)s') % {
                        'field': f,
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

    @classmethod
    def _validate_config_file(cls, theme_dir: Path):
        """ Validate that all configuration files contain required attributes. """
        valid_apps = get_valid_app_labels()
        template_attrs = ['name', 'action']

        for json_file in theme_dir.glob('*.json'):
            try:
                data = cls._read_json(json_file)
            except ThemeServiceError:
                continue

            # Validate theme config file
            if json_file.name.startswith('theme'):
                # Required: name
                if not data.get('name', ''):
                    raise ThemeServiceError(
                        _('Theme configuration file %(file)s is missing required field "name".') % {
                            'file': json_file.name,
                        }
                    )
                # Required: app_label
                app_label = data.get('app_label', '')
                if not app_label:
                    raise ThemeServiceError(
                        _('Theme configuration file %(file)s is missing required field "app_label".') % {
                            'file': json_file.name,
                        }
                    )
                if app_label not in valid_apps:
                    raise ThemeServiceError(
                        _('Theme configuration file %(file)s has unknown app_label "%(label)s".') % {
                            'file': json_file.name,
                            'label': app_label,
                        }
                    )
                continue

            for attr in template_attrs:
                if not data.get(attr, ''):
                    raise ThemeServiceError(
                        _('Template configuration file %(file)s is missing required field "%(attr)s".') % {
                            'file': json_file.name,
                            'attr': attr,
                        }
                    )

    # ------------------------------------------------------------------
    # Parse config (install-time)
    # ------------------------------------------------------------------

    @classmethod
    def _parse_config(cls, data: dict, config_file: str = '') -> dict:
        """
        Validate and parse vars and fieldsets from a JSON dict.
        Only the initial value (from 'default') is stored; definition fields
        (title, type, tip, options) are intentionally excluded.
        """
        cls._validate_config(data, config_file or 'config')

        result_vars = {}
        for key, var_def in data.get('vars', {}).items():
            var = ThemeVar.from_dict(var_def)
            result_vars[key] = cls._default_value(var)

        result_fieldsets = {}
        for fs_key, fs_def in data.get('fieldsets', {}).items():
            fs_vars = {}
            for var_key, var_def in fs_def.get('vars', {}).items():
                var = ThemeVar.from_dict(var_def)
                fs_vars[var_key] = cls._default_value(var)
            result_fieldsets[fs_key] = fs_vars

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
                'app_label': data.get('app_label', ''),
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
        theme_dir = cls._themes_root() / directory
        if not theme_dir.is_dir():
            raise ThemeServiceError(_('Theme directory not found: %(dir)s') % {'dir': directory})
        if Theme.objects.filter(directory=directory).exists():
            raise ThemeServiceError(_('Theme "%(dir)s" already installed.') % {'dir': directory})

        cls._validate_config_file(theme_dir)

        data = cls._read_json(theme_dir / 'theme.json')
        theme = Theme.objects.create(
            name=data.get('name', directory),
            app_label=data['app_label'],  # Required, has passed verification, fetch directly
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
            if json_file.name.startswith('theme'):
                continue

            data = cls._read_json(json_file)
            filename = json_file.name.split('.')[0]  # e.g. 'index' from 'index.json'
            ThemeTemplate.objects.create(
                theme=theme,
                filename=filename,
                name=data.get('name', ''),
                action=data.get('action', ''),
                sort_order=data.get('order', DEFAULT_SORT_ORDER),
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
        """Activate the given theme. Deactivates other themes in the same app."""
        theme = cls._get_theme(theme_id)
        Theme.objects.filter(app_label=theme.app_label).update(is_active=False)
        Theme.objects.filter(pk=theme_id).update(is_active=True)
        cls._invalidate_cache()

    # ------------------------------------------------------------------
    # Read config (for admin editing)
    # ------------------------------------------------------------------

    @classmethod
    def get_active_theme(cls, app_label: str) -> Optional[Theme]:
        """Return the currently active Theme, or None. Result is cached."""
        cache_key = f'{THEME_CACHE_KEY}:{app_label}'
        cached_pk = cache.get(cache_key)
        if cached_pk is not None:
            try:
                return Theme.objects.prefetch_related('templates').get(pk=cached_pk)
            except Theme.DoesNotExist:
                pass

        try:
            theme = Theme.objects.prefetch_related('templates').get(app_label=app_label, is_active=True)
            cache.set(cache_key, theme.pk, THEME_CACHE_TIMEOUT)

            # Track app_labels for bulk cache invalidation.
            app_labels = cache.get(THEME_CACHE_APP_LABELS_KEY) or []
            if app_label not in app_labels:
                app_labels.append(app_label)
                cache.set(THEME_CACHE_APP_LABELS_KEY, app_labels)
            return theme
        except Theme.DoesNotExist:
            return None

    @classmethod
    def get_templates_by_action(cls, app_label: str, action: str) -> list[ThemeTemplate]:
        """Return all ThemeTemplates of the active theme matching the given action."""
        theme = cls.get_active_theme(app_label)
        if theme is None:
            return []
        return [t for t in theme.templates.all() if t.action == action]

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

    @classmethod
    def get_template_choices(cls, app_label: str, action: str):
        """Return template choices for the given action, with default option first."""
        return [(action, _('Default'))] + [
            (t.filename, t.name)
            for t in cls.get_templates_by_action(app_label, action)
            if t.filename != action
        ]

    # ------------------------------------------------------------------
    # Save config
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_submitted_values(config: dict, submitted: dict) -> dict:
        """
        Write submitted POST values into a stored config dict.
        Only existing keys are updated; unknown keys are silently ignored.
        """
        for key, value in submitted.get('vars', {}).items():
            if key in config.get('vars', {}):
                config['vars'][key] = value

        for fs_key, fs_values in submitted.get('fieldsets', {}).items():
            if fs_key in config.get('fieldsets', {}):
                for var_key, value in fs_values.items():
                    if var_key in config['fieldsets'][fs_key]:
                        config['fieldsets'][fs_key][var_key] = value

        return config

    @classmethod
    def get_var_definitions(
            cls,
            theme_id: int,
            template_id: int | None,
    ) -> dict[str, ThemeVar]:
        """
        Return a flat mapping of POST field name -> ThemeVar for all
        configurable variables in the given theme or template config file.

        Key format matches _render_var naming convention:
          top-level var -> 'var__<key>'
          fieldset var  -> 'fieldset__<fs_key>__<var_key>'

        Used by collect_submitted to look up each field's type during POST
        processing, without re-reading the file a second time.
        """
        theme = cls._get_theme(theme_id)
        theme_dir = cls._themes_root() / theme.directory

        if template_id:
            current_template = cls._get_template(template_id)
            file_data = cls._read_config(theme_dir / f'{current_template.filename}.json')
        else:
            file_data = cls._read_config(theme_dir / 'theme.json')

        result: dict[str, ThemeVar] = {}

        for key, var_def in file_data.get('vars', {}).items():
            result[f'var__{key}'] = ThemeVar.from_dict(var_def)

        for fs_key, fs_def in file_data.get('fieldsets', {}).items():
            for var_key, var_def in fs_def.get('vars', {}).items():
                result[f'fieldset__{fs_key}__{var_key}'] = ThemeVar.from_dict(var_def)

        return result

    @classmethod
    def collect_submitted(
            cls,
            post_data: QueryDict,
            var_definitions: dict[str, ThemeVar],
    ) -> dict:
        """
        Extract and coerce POST values using Django Widget machinery.

        For each known field name, delegates to Widget.value_from_datadict()
        rather than reading request.POST directly. This is critical for boolean
        fields (PinmokSwitch): when a checkbox is unchecked it is absent from POST,
        and value_from_datadict() correctly returns False in that case.

        Unknown POST keys are ignored. If no widget is found for a var (e.g.
        unregistered datasource), falls back to raw string from POST.

        Returns a dict shaped for _apply_submitted_values:
          {'vars': {key: value, ...}, 'fieldsets': {fs_key: {key: value, ...}}}
        """
        submitted_vars: dict = {}
        submitted_fieldsets: dict = {}

        for field_name, var in var_definitions.items():
            widget = cls.get_widget_for_var(var)

            if widget is None:
                # datasource not registered; no widget available, skip this field.
                continue

            # Delegate extraction to the widget. value_from_datadict receives
            # the full QueryDict so it can handle multi-value fields correctly.
            # The files argument is unused for non-file widgets; pass empty dict.
            value = widget.value_from_datadict(post_data, MultiValueDict(), field_name)

            # Decode field_name back into the storage structure.
            parts = field_name.split('__', 2)
            if parts[0] == 'var':
                # 'var__<key>'
                submitted_vars[parts[1]] = value
            elif parts[0] == 'fieldset':
                # 'fieldset__<fs_key>__<var_key>'
                submitted_fieldsets.setdefault(parts[1], {})[parts[2]] = value

        return {'vars': submitted_vars, 'fieldsets': submitted_fieldsets}

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
    def get_template_path(cls, app_label: str, filename: str) -> Optional[str]:
        """Return the full template path for the given filename, or None if no active theme."""
        theme = cls.get_active_theme(app_label)
        if theme is None:
            return None
        return f'themes/{theme.directory}/{filename}.html'

    @classmethod
    def get_vars_context(cls, app_label: str, filename: str) -> dict:
        """
        Return a dict of variable values for the given action,
        merging global (theme-level) vars and page-level vars.
        Page-level vars override global vars on key collision.

        Top-level vars are injected directly: {{ company_name }}
        Fieldset vars are injected as dicts: {{ news.category }}

        Used by views to inject theme variables into the template context.
        """

        def extract(config: dict) -> dict:
            result = {}
            # Top-level vars
            for key, value in config.get('vars', {}).items():
                result[key] = value
            # Fieldsets as nested dicts
            for fs_key, fs_vars in config.get('fieldsets', {}).items():
                result[fs_key] = dict(fs_vars)
            return result

        theme = cls.get_active_theme(app_label)
        if theme is None:
            return {}

        context = extract(theme.config)

        try:
            template = theme.templates.get(filename=filename)
            context.update(extract(template.config))
        except ThemeTemplate.DoesNotExist:
            pass

        return context

    # ------------------------------------------------------------------
    # Config context for admin editing page
    # ------------------------------------------------------------------

    @classmethod
    def _render_var(cls, key: str, var_def: dict, value: Any, fs_key: str = '') -> dict:
        """
        Convert a single var definition and its stored value into a template-friendly dict.
        var_def comes from the config file; value comes from the database config field.
        fs_key is non-empty when the var belongs to a fieldset.
        """
        var = ThemeVar.from_dict(var_def)
        name = f'fieldset__{fs_key}__{key}' if fs_key else f'var__{key}'
        widget = cls.get_widget_for_var(var)
        html = widget.render(name, value) if widget else ''

        return {
            'key': key,
            'title': var.title,
            'tip': var.tip,
            'html': html,
            'value': value
        }

    @classmethod
    def _build_config_context(cls, file_data: dict, db_config: dict) -> dict:
        """
        Build the template-friendly config structure for the admin editing page.
        file_data is the parsed config file (provides definitions: title, type, tip, options).
        db_config is the stored database config (provides saved values only).
        """
        rendered_vars = [
            cls._render_var(key, var_def, db_config.get('vars', {}).get(key, ''))
            for key, var_def in file_data.get('vars', {}).items()
        ]

        rendered_fieldsets = []
        for fs_key, fs_def in file_data.get('fieldsets', {}).items():
            fields = [
                cls._render_var(
                    var_key,
                    var_def,
                    db_config.get('fieldsets', {}).get(fs_key, {}).get(var_key, ''),
                    fs_key,
                )
                for var_key, var_def in fs_def.get('vars', {}).items()
            ]
            rendered_fieldsets.append({
                'key': fs_key,
                'title': fs_def.get('title', fs_key),
                'fields': fields,
            })

        return {
            'vars': rendered_vars,
            'fieldsets': rendered_fieldsets,
        }

    @classmethod
    def _read_config(cls, base_path: Path) -> dict:
        """
        Read a config JSON file with language fallback.
        Tries the current language variant first (e.g. theme.zh-hans.json),
        falls back to the default file (e.g. theme.json) if not found.
        Language code must match Django's get_language() format exactly.
        """
        lang_path = base_path.with_name(f'{base_path.stem}.{get_language()}{base_path.suffix}')
        if lang_path.exists():
            return cls._read_json(lang_path)
        return cls._read_json(base_path)

    @classmethod
    def get_config_context(cls, theme_id: int, template_id: int | None) -> dict:
        """
        Return all data needed for the config editing page.

        Reads variable definitions from the config file (with language fallback),
        merges with saved values from the database config field, and resolves
        widget instances for each var.

        config_data contains two lists ready for template iteration:
        - vars: list of field dicts (key, title, tip, HTML, value)
        - fieldsets: list of group dicts (key, title, fields), where each
          fields entry has the same shape as a vars field dict.
        """
        theme = cls._get_theme(theme_id)
        templates = ThemeTemplate.objects.filter(theme=theme).order_by('sort_order', 'name')
        theme_dir = cls._themes_root() / theme.directory

        if template_id:
            current_template = cls._get_template(template_id)
            file_data = cls._read_config(theme_dir / f'{current_template.filename}.json')
            db_config = cls.get_template_config(template_id)
        else:
            current_template = None
            file_data = cls._read_config(theme_dir / 'theme.json')
            db_config = cls.get_theme_config(theme_id)

        config_data = cls._build_config_context(file_data, db_config)

        return {
            'theme': theme,
            'templates': templates,
            'current_template': current_template,
            'config_data': config_data,
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
            source = var.options.get('source')
            widget_class = datasource.get(source)
            if widget_class:
                # The widget class may not declare **kwargs, so we filter options to only
                # pass parameters it explicitly accepts. If it does declare **kwargs,
                # pass all options and let the widget handle them itself.
                sig = inspect.signature(widget_class.__init__)
                params = sig.parameters
                has_var_keyword = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in params.values()
                )
                options = var.options if has_var_keyword else {k: v for k, v in var.options.items() if k in params}
                return widget_class(**options)
            return None

        widget_class = TYPE_WIDGET_MAP.get(var.type)
        return widget_class() if widget_class else None  # type: ignore
