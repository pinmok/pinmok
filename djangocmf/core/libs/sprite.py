#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sprite icons manager class

Description:
  Manage an SVG sprite file via Django default_storage.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
import os
from xml.etree import ElementTree

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Register SVG namespace globally to avoid 'ns0' prefixes in output
ElementTree.register_namespace('', 'http://www.w3.org/2000/svg')


class SpriteError(Exception):
    """Custom exception for sprite operation errors."""
    pass


class SpriteManager:
    """
    Manage an SVG sprite file containing multiple <symbol> elements.

    All file operations go through Django's default_storage, supporting
    local filesystem, S3, and other storage backends transparently.

    The sprite file must exist before instantiation. Use create() to
    initialize a new sprite file.

    Attributes:
        sprite_file (str): Relative path to the SVG sprite file (relative to MEDIA_ROOT).
        _viewbox (str): Default viewBox attribute for generated symbols.
        SVG_NS (dict): Namespace mapping for SVG parsing.

    Methods:
        create(sprite_file)
        add(symbol_id, svg_str)
        remove(symbol_id)
        update(symbol_id, svg_str)
        has(symbol_id) -> bool
        list_symbols() -> list
    """

    SVG_NS = {'svg': 'http://www.w3.org/2000/svg'}

    def __init__(self, sprite_file: str, viewbox: str = '0 0 24 24'):
        """
        Initialize the SpriteManager instance.

        The sprite file must already exist. Use SpriteManager.create() to
        initialize a new sprite file before instantiating.

        Args:
            sprite_file (str): Relative path to the SVG sprite file (relative to MEDIA_ROOT).
            viewbox (str): Default viewBox attribute for generated symbols.

        Raises:
            ValueError: If sprite_file is empty or None, or if the file has invalid XML.
            SpriteError: If the sprite file does not exist.
        """
        if not sprite_file:
            raise ValueError("sprite_file path cannot be None or empty.")

        self.sprite_file = sprite_file
        self._viewbox = viewbox

        if not default_storage.exists(self.sprite_file):
            raise SpriteError(f"Sprite file '{self.sprite_file}' not found.")

        try:
            with default_storage.open(self.sprite_file, 'r') as f:
                content = f.read()
            # default_storage.open() may return bytes depending on the backend
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            self.root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            raise ValueError(f"Sprite file '{self.sprite_file}' format error")

    @staticmethod
    def create(sprite_file: str):
        """
        Create an empty sprite file with base SVG root.

        Args:
            sprite_file (str): Relative path where the sprite file should be created
                               (relative to MEDIA_ROOT).

        Raises:
            SpriteError: If the file already exists or creation fails.
        """
        if default_storage.exists(sprite_file):
            raise SpriteError('File already exists')

        try:
            empty_svg = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n</svg>'
            default_storage.save(sprite_file, ContentFile(empty_svg.encode('utf-8')))
        except Exception as e:
            raise SpriteError(f'Failed to create sprite file: {e}')

    def _save_sprite(self):
        """
        Write the current XML tree back to the sprite file.

        Uses delete-then-save to guarantee the file path stays fixed,
        since default_storage.save() may rename files when they already exist.
        """
        try:
            new_content = ElementTree.tostring(self.root, encoding='unicode')
            # Delete first to prevent storage backends from renaming the file
            if default_storage.exists(self.sprite_file):
                default_storage.delete(self.sprite_file)
            default_storage.save(self.sprite_file, ContentFile(new_content.encode('utf-8')))
        except Exception as e:
            raise SpriteError(f'Failed to save sprite file: {e}')

    def _find_symbol(self, symbol_id: str) -> ElementTree.Element | None:
        """Find a <symbol> element by ID."""
        if not symbol_id:
            return None
        return next(
            (e for e in self.root.findall('svg:symbol', self.SVG_NS) if e.attrib.get('id') == symbol_id),
            None
        )

    def _svg_to_symbol(self, symbol_id: str, svg_raw: str) -> str:
        """Convert an SVG string into a <symbol> string."""
        try:
            root = ElementTree.fromstring(svg_raw)
        except ElementTree.ParseError as e:
            raise ValueError(f"SVG parse error in symbol '{symbol_id}': {e}")

        if not root.tag.endswith('svg'):
            raise ValueError(f"Input content is not an <svg> element for symbol '{symbol_id}'")

        symbol = ElementTree.Element('symbol', id=symbol_id)

        # Copy viewBox or set default
        symbol.set('viewBox', root.attrib.get('viewBox', self._viewbox))

        # Copy all display-relevant attributes, skip metadata and layout attrs
        skip_attrs = {'xmlns', 'id', 'class', 'width', 'height', 'version', 'xml:space', 'viewBox'}
        for attr, value in root.attrib.items():
            if attr not in skip_attrs:
                symbol.set(attr, value)

        # Detect filled icon by checking root fill attribute
        is_filled = root.attrib.get('fill') == 'currentColor'

        # Remove namespace prefix from child tags and append to symbol
        for child in root:
            if '}' in child.tag:
                child.tag = child.tag.split('}', 1)[1]
            # Lock fill/stroke on each child to prevent inheritance from outer <svg>
            if is_filled:
                if 'fill' not in child.attrib:
                    child.set('fill', 'currentColor')
                if 'stroke' not in child.attrib:
                    child.set('stroke', 'none')
            symbol.append(child)

        return ElementTree.tostring(symbol, encoding='unicode')

    def get(self, symbol_id: str) -> str:
        """
        Retrieve a symbol's content as a standard <svg> string.

        Converts the stored <symbol> back to an <svg> element so it can be
        displayed in the edit form and resubmitted through the normal flow.

        Args:
            symbol_id (str): The symbol ID to retrieve.

        Returns:
            str: SVG string with the symbol's content wrapped in an <svg> element.

        Raises:
            SpriteError: If the symbol_id is not found.
        """
        target = self._find_symbol(symbol_id)
        if not target:
            raise SpriteError(f"symbol_id '{symbol_id}' not found")

        svg = ElementTree.Element('{http://www.w3.org/2000/svg}svg')

        # Restore all attributes from symbol back to svg root (skip symbol-specific ones)
        for attr, value in target.attrib.items():
            if attr != 'id':
                svg.set(attr, value)

        # Copy child elements
        for child in target:
            svg.append(child)

        return ElementTree.tostring(svg, encoding='unicode')

    def add(self, symbol_id: str, svg_str: str):
        """
        Add a new <symbol> to the sprite file.

        Raises:
            SpriteError: If the symbol_id already exists or the operation fails.
        """
        if self._find_symbol(symbol_id):
            raise SpriteError(f'symbol_id "{symbol_id}" already exists')

        try:
            symbol_str = self._svg_to_symbol(symbol_id, svg_str)
            new_symbol = ElementTree.fromstring(symbol_str)
            self.root.append(new_symbol)
            self._save_sprite()
        except (ValueError, ElementTree.ParseError) as e:
            raise SpriteError(str(e))
        except Exception as e:
            raise SpriteError(f'Failed to add symbol: {e}')

    def remove(self, symbol_id: str):
        """
        Remove a <symbol> by its ID.

        Raises:
            SpriteError: If the symbol_id is not found or the operation fails.
        """
        target_symbol = self._find_symbol(symbol_id)
        if not target_symbol:
            raise SpriteError(f"symbol_id '{symbol_id}' not found, cannot delete")

        try:
            self.root.remove(target_symbol)
            self._save_sprite()
        except Exception as e:
            raise SpriteError(f'Failed to remove symbol: {e}')

    def update(self, symbol_id: str, svg_str: str):
        """
        Update an existing <symbol> by its ID.

        Replaces the symbol in-place to avoid data loss if add() fails.

        Raises:
            SpriteError: If the symbol_id is not found or the operation fails.
        """
        target = self._find_symbol(symbol_id)
        if not target:
            raise SpriteError(f"symbol_id '{symbol_id}' not found, cannot update")

        try:
            symbol_str = self._svg_to_symbol(symbol_id, svg_str)
            new_symbol = ElementTree.fromstring(symbol_str)
            children = list(self.root)
            idx = children.index(target)
            self.root.remove(target)
            self.root.insert(idx, new_symbol)
            self._save_sprite()
        except (ValueError, ElementTree.ParseError) as e:
            raise SpriteError(str(e))
        except Exception as e:
            raise SpriteError(f'Failed to update symbol: {e}')

    def has(self, symbol_id: str) -> bool:
        """Check if a <symbol> exists."""
        return self._find_symbol(symbol_id) is not None

    def list_symbols(self) -> list:
        """List all <symbol> IDs in the sprite file."""
        return [
            e.attrib.get('id')
            for e in self.root.findall('svg:symbol', self.SVG_NS)
            if e.attrib.get('id')
        ]

    @staticmethod
    def list_system_symbols(system_sprite_path: str) -> list:
        """
        Read symbol IDs from the system sprite file served under STATIC_ROOT.
        Uses direct file I/O since static files are local and read-only.

        Args:
            system_sprite_path (str): Absolute path to the system sprite file.

        Returns:
            list: List of symbol IDs found in the sprite file.

        Raises:
            SpriteError: If the file does not exist or cannot be parsed.
        """
        if not os.path.exists(system_sprite_path):
            raise SpriteError(f"System sprite file '{system_sprite_path}' not found.")

        try:
            with open(system_sprite_path, 'r', encoding='utf-8') as f:
                content = f.read()
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            raise SpriteError(f"System sprite file '{system_sprite_path}' format error")

        return [
            e.attrib.get('id')
            for e in root.findall('svg:symbol', SpriteManager.SVG_NS)
            if e.attrib.get('id')
        ]
