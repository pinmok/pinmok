#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dedupe_po module

Description:
  Django Management Command for PO File Deduplication
  Provides a command-line interface for the PO deduplication tool.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-25
"""
import sys

from django.core.management import BaseCommand, CommandParser

from djangocmf.core.libs.console import Console, MessageLevel
from djangocmf.core.utils.po_deduplicator import PoDeduplicator


class Command(BaseCommand):
    """Django management command for PO file deduplication."""
    help = 'PO File Deduplication Tool for Django Projects'

    def add_arguments(self, parser: CommandParser) -> None:
        """Register command-line arguments using the shared argument definitions."""
        PoDeduplicator.add_po_dedupe_arguments(parser)

    def handle(self, *args, **options):
        """Main command execution logic."""
        # Initialize console with Django command context for proper output styling
        console = Console(django_command=self, verbose=True)

        def django_emit(level: MessageLevel, message: str, metadata: dict) -> None:
            """Map progress events to colored console output."""
            console.output(level, message, **metadata)

        try:
            deduper = PoDeduplicator(
                lang=options["lang"],
                domain=options["domain"],
                base_dir=options["directory"],
                backup=options["no_backup"],
                keep_comments=options["no_comments"],
                emit_progress=django_emit,
            )

            deduper.handle()
        except Exception as e:
            console.error("Deduplication failed", error=str(e))
            sys.exit(1)
