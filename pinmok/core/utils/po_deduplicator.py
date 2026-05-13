#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
po_deduplicator module

Description:
  PO File Deduplication Tool for Django Projects
  This script removes duplicate entries within .po files and optionally
  deduplicates them against system or base PO files.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-13
"""
import argparse
import datetime
import os
import site
import sys
from collections.abc import Callable
from dataclasses import dataclass

from django.utils.translation import to_locale

from pinmok.core.libs.console import Console, MessageLevel

try:
    import polib
except ImportError:
    if __name__ == "__main__":
        Console().error("polib is not installed. Please install it via `pip install polib`.")
        sys.exit(1)
    else:
        raise ImportError("polib is required for po_tool to function.")


@dataclass
class PoDedupeResult:
    file: str = ""
    original: int = 0
    removed: int = 0
    remaining: int = 0
    backup_path: str = ""
    backup_created: bool = False


class PoDeduplicator:
    """Core deduplication logic for .po files."""

    SYSTEM_PACKAGES = [
        "django/contrib/admin",
        "django/contrib/auth",
        "django/contrib/contenttypes",
        "django/contrib/flatpages",
    ]

    DOMAIN = {'django', 'djangojs'}

    def __init__(
            self,
            lang: str = 'zh-hans',
            domain: str | list[str] | None = None,
            base_dir: str | None = None,
            backup: bool = True,
            keep_comments: bool = True,
            emit_progress: Callable[[MessageLevel, str, dict], None] | None = None
    ):
        """ Instance mode — used when we want callback support. """
        self.lang = lang
        self.domains = self._validate_domains(domain)
        self.base_dir = base_dir or os.getcwd()
        self.backup = backup
        self.keep_comments = keep_comments
        self._emit_progress = emit_progress
        self._all_system_msgids: dict[str, set[str]] = {}

    def _validate_domains(self, domain: str | list[str] | None) -> set[str]:
        if not domain:
            return self.DOMAIN
        elif isinstance(domain, list):
            invalid = [d for d in domain if d not in self.DOMAIN]
            if invalid:
                raise ValueError(f"Invalid domains: {invalid}")
            return set(domain)
        else:
            if domain not in self.DOMAIN:
                raise ValueError(f"Invalid domain: {domain}")
            return {domain}

    def _emit(self, level: MessageLevel, message: str, **metadata):
        """Emit a progress event if a callback is configured, otherwise do nothing."""
        if self._emit_progress:
            self._emit_progress(level, message, metadata)

    def _load_all_system_msgids(self, domain: str):
        """Load and cache msgids for a single domain."""
        if domain in self._all_system_msgids:
            return self._all_system_msgids[domain]

        system_keys = set()
        sys_po_files = self._get_system_po_files(domain)

        for po_file in sys_po_files:
            try:
                po = polib.pofile(po_file, encoding="utf-8")
                for entry in po:
                    if entry.msgid != "":
                        system_keys.add((entry.msgctxt, entry.msgid, entry.msgid_plural))
            except Exception as e:
                self._emit(MessageLevel.ERROR, str(e), file=po_file)
                continue

        self._all_system_msgids[domain] = system_keys
        return system_keys

    def _get_source_files(self, domain: str) -> list[str]:
        """Generate all source .po files, excluding system site-packages."""
        po_files: list[str] = []
        seen: set[str] = set()

        expected_rel = os.path.normpath(os.path.join("locale", to_locale(self.lang), "LC_MESSAGES"))
        project_root = os.path.abspath(self.base_dir)

        site_roots = [
            os.path.abspath(p)
            for p in (site.getsitepackages() + [site.getusersitepackages()])
        ]

        self._emit(MessageLevel.INFO, "Scanning source po files...")
        for root, dirs, files in os.walk(project_root):
            abs_root = os.path.abspath(root)

            # exclude system packages
            if any(abs_root.startswith(sr) for sr in site_roots):
                continue

            # match locale/<lang>/LC_MESSAGES
            if not os.path.normpath(root).endswith(expected_rel):
                continue

            candidate = os.path.join(root, f"{domain}.po")
            if os.path.isfile(candidate):
                abs_path = os.path.abspath(candidate)
                if abs_path not in seen:
                    seen.add(abs_path)
                    po_files.append(abs_path)
                    self._emit(MessageLevel.INFO, "File found.", file=abs_path)

        return sorted(po_files)

    def _get_system_po_files(self, domain: str) -> list[str]:
        """Scan system PO files"""
        po_files = []

        bases = site.getsitepackages()
        user_site = site.getusersitepackages()
        if user_site not in bases:
            bases.append(user_site)

        for base in bases:
            for pkg in self.SYSTEM_PACKAGES:
                po_path = os.path.join(base, pkg, "locale", to_locale(self.lang), "LC_MESSAGES", f"{domain}.po")
                if os.path.isfile(po_path):
                    po_files.append(po_path)

        return po_files

    def _make_backup(self, file_path: str) -> str:
        """Create timestamped backup of the source file."""
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_{timestamp}.bak"

        try:
            with open(file_path, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            self._emit(MessageLevel.ERROR, "Failed to create backup", backup_path=backup_path, error=str(e))
            return ""

        return backup_path

    def process_one(self, source_po: str, domain: str) -> PoDedupeResult:
        """ Process a single PO file. """
        self._emit(MessageLevel.STEP, "Processing PO file...", file=source_po, domain=domain)

        try:
            # Load polib
            po = polib.pofile(source_po, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Failed to parse PO file: {source_po}") from e

        original_count = len(po)

        # load system keys
        if domain not in self._all_system_msgids:
            self._load_all_system_msgids(domain)
        system_keys = self._all_system_msgids.get(domain, set())

        # self dedupe and system dedupe
        seen = set()
        new_entries = []

        header_entry = None
        for entry in po:
            # skip header (already handled)
            if entry.msgid == "":
                header_entry = entry
                continue

            # unique key with msgctxt
            key = (entry.msgctxt, entry.msgid, entry.msgid_plural)

            if key in seen:
                continue
            if key in system_keys:
                continue
            seen.add(key)
            new_entries.append(entry)

        # restore header at top
        if header_entry:
            new_entries.insert(0, header_entry)

        removed_count = original_count - len(new_entries)
        modified = removed_count > 0

        if not modified:
            self._emit(MessageLevel.INFO, "File unchanged", file=source_po, original_count=original_count)
            return PoDedupeResult(file=source_po, original=original_count, remaining=original_count)

        # clear comments if needed
        if not self.keep_comments:
            for e in new_entries:
                if e.msgid != "":
                    e.comment = ""
                    e.tcomment = ""

        # backup
        backup_path = ""
        backup_created = False
        if self.backup and modified:
            backup_path = self._make_backup(source_po)
            backup_created = True
            self._emit(MessageLevel.INFO, "Backup created", file=source_po, backup_path=backup_path)

        # --- overwrite entries safely ---
        po.clear()  # clear all
        for e in new_entries:
            po.append(e)
        po.save(source_po)

        self._emit(
            MessageLevel.SUCCESS,
            "File processed",
            file=source_po,
            original=original_count,
            removed=removed_count,
            remaining=len(new_entries),
            backup_path=backup_path
        )

        return PoDedupeResult(
            file=source_po,
            original=original_count,
            removed=removed_count,
            remaining=len(new_entries),
            backup_path=backup_path,
            backup_created=backup_created
        )

    def handle(self) -> list[PoDedupeResult]:
        """
        Handle deduplication for all domains and all found source files.
        This is the instance-mode version with callback support.
        """
        self._emit(
            MessageLevel.STEP,
            "Starting PO deduplication...",
            lang=self.lang,
            domains=self.domains
        )

        results = []
        for domain in self.domains:
            # load sys entries
            self._load_all_system_msgids(domain)

            # source list
            source_files = self._get_source_files(domain)

            self._emit(MessageLevel.STEP, "Processing domain...", domain=domain, files_count=len(source_files))

            for src in source_files:
                try:
                    result = self.process_one(src, domain)
                    results.append(result)
                except Exception as e:
                    self._emit(MessageLevel.ERROR, "Failed to process file", file=src, error=str(e))
                    continue

            self._emit(
                MessageLevel.SUCCESS,
                "Domain completed",
                domain=domain,
                files_count=len(source_files)
            )

        total_removed = sum(r.removed for r in results)
        self._emit(
            MessageLevel.STEP_DONE,
            "Deduplication completed successfully",
            total_files=len(results),
            total_removed=total_removed
        )

        return results

    @staticmethod
    def add_po_dedupe_arguments(parser):
        """Register CLI arguments for the PO deduplication command."""
        parser.add_argument(
            "-l", "--lang",
            default="zh-hans",
            dest="lang",
            metavar="LANGUAGE_CODE",
            help="Language code (default zh-hans)"
        )
        parser.add_argument(
            "-d", "--domain",
            choices=["django", "djangojs"],
            nargs="+",
            help="Limit to specific domain"
        )
        parser.add_argument(
            "--dir", "--directory",
            default=None,
            dest="directory",
            metavar="SCAN_DIRECTORY",
            help="Base directory to scan (default: current directory)"
        )
        parser.add_argument(
            "--no-backup",
            action="store_false",
            default=True,
            help="Do not create backup before cleaning"
        )
        parser.add_argument(
            "--no-comments",
            action="store_false",
            default=True,
            help="Do not preserve comments"
        )


# ---------------
# CLI main entry
# ---------------
def main():
    parser = argparse.ArgumentParser(description="PO File Deduplication Tool for Django Projects")
    PoDeduplicator.add_po_dedupe_arguments(parser)
    args = parser.parse_args()

    console = Console(verbose=True)

    def cli_emit(level: MessageLevel, message: str, metadata: dict) -> None:
        """Map progress events to colored console output."""
        console.output(level, message, **metadata)

    try:
        deduper = PoDeduplicator(
            lang=args.lang,
            domain=args.domain,
            base_dir=args.directory,
            backup=args.no_backup,
            keep_comments=args.no_comments,
            emit_progress=cli_emit
        )

        deduper.handle()
    except Exception as e:
        console.error(f"An error has occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
