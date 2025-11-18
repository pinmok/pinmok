#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sprite icons manager class

Description:
  Manage an SVG sprite file
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-08
"""
import os
from xml.etree import ElementTree as ET


class SpriteError(Exception):
    """Custom exception for sprite operation errors."""
    pass


class SpriteManager:
    """
    Manage an SVG sprite file containing multiple <symbol> elements.

    This class provides methods to add, remove, update, check existence,
    and list SVG symbols within a sprite file.

    Attributes:
        sprite_file (str): Path to the SVG sprite file.
        _viewbox (str): Default viewBox attribute for generated symbols.
        SVG_NS (dict): Namespace mapping for SVG parsing.

    Methods:
        create()
        add(symbol_id, svg_str)
        remove(symbol_id)
        update(symbol_id, svg_str)
        has(symbol_id) -> bool
        list() -> list
    """

    SVG_NS = {'svg': 'http://www.w3.org/2000/svg'}

    def __init__(self, sprite_file: str, viewbox: str = '0 0 24 24'):
        """
        Initialize the SpriteManager instance.

        Attempts to read the SVG sprite file from the given path.
        If the file does not exist, creates an empty sprite file with a base SVG root,
        then loads it.

        Args:
            sprite_file (str): Path to the SVG sprite file.
            viewbox (str): Default viewBox attribute for generated symbols.
        """
        self.sprite_file = sprite_file
        self._viewbox = viewbox

        if not sprite_file:
            raise ValueError("sprite_file path cannot be None or empty.")

        # Create file if not exists.
        if not os.path.exists(self.sprite_file):
            dir_path = os.path.dirname(self.sprite_file)
            os.makedirs(dir_path, exist_ok=True)
            with open(self.sprite_file, 'w', encoding='utf-8') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n</svg>')

        try:
            with open(self.sprite_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.root = ET.fromstring(content)
        except ET.ParseError:
            raise ValueError(f"Sprite file '{self.sprite_file}' format error")

    def _save_sprite(self):
        """Save the updated sprite XML to file."""
        try:
            new_content = ET.tostring(self.root, encoding='unicode')
            with open(self.sprite_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            raise SpriteError(f'Failed to save sprite file: {e}')

    def _find_symbol(self, symbol_id: str) -> ET.Element | None:
        """Find a <symbol> element by ID."""
        if not symbol_id:
            return None
        return next((e for e in self.root.findall('svg:symbol', self.SVG_NS) if e.attrib.get('id') == symbol_id), None)

    def _svg_to_symbol(self, symbol_id: str, svg_raw: str) -> str:
        """Convert an SVG string into a <symbol> string."""

        # Register the SVG namespace with an empty prefix to avoid 'ns0' or other prefixes in the output
        ET.register_namespace('', 'http://www.w3.org/2000/svg')

        try:
            root = ET.fromstring(svg_raw)
        except ET.ParseError as e:
            raise ValueError(f"SVG parse error in symbol '{symbol_id}': {e}")

        if not root.tag.endswith('svg'):
            raise ValueError(f"Input content is not an <svg> element for symbol '{symbol_id}'")

        symbol = ET.Element('symbol', id=symbol_id)

        # Copy viewBox or set default
        symbol.set('viewBox', root.attrib.get('viewBox', self._viewbox))

        # Copy common SVG attributes if present
        common_attrs = ['fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin']
        for attr in common_attrs:
            value = root.attrib.get(attr)
            if value:
                symbol.set(attr, value)

        # Remove namespace prefix from child tags and append to symbol
        for child in root:
            if '}' in child.tag:
                child.tag = child.tag.split('}', 1)[1]
            symbol.append(child)

        return ET.tostring(symbol, encoding='unicode')

    def create(self):
        """Create an empty sprite file with base SVG root."""
        if os.path.exists(self.sprite_file):
            raise SpriteError('File already exists')

        try:
            with open(self.sprite_file, 'w', encoding='utf-8') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n</svg>')
        except Exception as e:
            raise SpriteError(f'Failed to create sprite file: {e}')

    def add(self, symbol_id: str, svg_str: str):
        """Add a new <symbol> to the sprite file."""

        # Search for existing <symbol> element by ID
        if self._find_symbol(symbol_id):
            raise SpriteError(f'symbol_id "{symbol_id}" already exists')

        try:
            # Parse the new symbol XML string
            symbol_str = self._svg_to_symbol(symbol_id, svg_str)
            new_symbol = ET.fromstring(symbol_str)

            # Append new symbol to SVG root
            self.root.append(new_symbol)
            self._save_sprite()
        except (ValueError, ET.ParseError) as e:
            raise SpriteError(str(e))
        except Exception as e:
            raise SpriteError(f'Failed to add symbol: {e}')

    def remove(self, symbol_id: str):
        """Remove a <symbol> by its ID."""

        # Search for existing <symbol> element by ID
        target_symbol = self._find_symbol(symbol_id)
        if not target_symbol:
            raise SpriteError(f"symbol_id '{symbol_id}' not found, cannot delete")

        try:
            self.root.remove(target_symbol)
            self._save_sprite()
        except Exception as e:
            raise SpriteError(f'Failed to remove symbol: {e}')

    def update(self, symbol_id: str, svg_str: str):
        """Update an existing <symbol> by its ID."""
        self.remove(symbol_id)
        self.add(symbol_id, svg_str)

    def has(self, symbol_id: str) -> bool:
        """Check if a <symbol> exists."""
        return self._find_symbol(symbol_id) is not None

    def list(self) -> list:
        """List all <symbol> IDs."""
        return [e.attrib.get('id') for e in self.root.findall('svg:symbol', self.SVG_NS) if e.attrib.get('id')]
