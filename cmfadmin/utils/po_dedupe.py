#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
po_dedupe module

Description:
  PO File Deduplication Tool for Django Projects
    This script removes duplicate entries within .po files and optionally
    deduplicates them against system or base PO files (such as Django and
    custom admin translations).
  Features:
    - Deduplicate msgid entries within a PO file.
    - Remove entries already present in system reference PO files.
    - Automatically backup modified files (timestamped).
    - Support both single-file and recursive batch processing.
    - Designed for Django i18n directories.
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
from dataclasses import dataclass
from pathlib import Path

# keep original
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from cmfadmin.libs.console import Console

try:
    import polib
except ImportError:
    if __name__ == "__main__":
        Console.error("polib is not installed. Please install it via `pip install polib`.")
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
        "django/conf",
        "django/contrib/admin",
        "django/contrib/auth",
        "cmfadmin",
    ]

    DOMAIN = ('django', 'djangojs')

    _all_system_msgids: dict[str, set[str]] = {}

    def __init__(self, lang, domain, backup=True, keep_comments=True, progress_callback=None):
        """ Instance mode — used when we want callback support. """
        self.lang = lang
        self.domain = domain
        self.backup = backup
        self.keep_comments = keep_comments
        self.progress_callback = progress_callback

    def _emit_progress(self, event: dict):
        """Emit a progress event to the external callback."""
        if self.progress_callback is not None:
            self.progress_callback(event)

    @classmethod
    def _load_all_system_msgids(cls, lang: str, domain: str):
        """Load and cache msgids for a single domain."""
        if domain in cls._all_system_msgids:
            return cls._all_system_msgids[domain]

        merged = set()
        sys_po_files = cls._get_system_po_files(lang, domain)
        for po_file in sys_po_files:
            po = polib.pofile(po_file, encoding="utf-8")
            merged.update(e.msgid for e in po if e.msgid != "")
        cls._all_system_msgids[domain] = merged
        return merged

    @classmethod
    def _get_source_files(cls, lang: str, domain: str) -> list[str]:
        """Generate all source .po files, excluding system site-packages."""
        po_files: list[str] = []
        seen: set[str] = set()

        expected_rel = os.path.normpath(os.path.join("locale", lang, "LC_MESSAGES"))
        project_root = os.path.abspath(os.getcwd())

        site_roots = [
            os.path.abspath(p)
            for p in (site.getsitepackages() + [site.getusersitepackages()])
        ]

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

        return sorted(po_files)

    @classmethod
    def _get_system_po_files(cls, lang: str, domain: str) -> list[str]:
        """Scan system PO files"""
        po_files = []

        bases = site.getsitepackages()
        user_site = site.getusersitepackages()
        if user_site not in bases:
            bases.append(user_site)

        for base in bases:
            for pkg in cls.SYSTEM_PACKAGES:
                po_path = os.path.join(base, pkg, "locale", lang, "LC_MESSAGES", f"{domain}.po")
                if os.path.exists(po_path):
                    po_files.append(po_path)
        return po_files

    @staticmethod
    def _make_backup(file_path: str) -> str:
        """Create timestamped backup of the source file."""
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_{timestamp}.bak"
        with open(file_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
        return backup_path

    def process_one(self, source_po: str, domain: str) -> PoDedupeResult:
        """
        Process a single PO file.
        """
        self._emit_progress({"event": "processing", "file": source_po})

        # Load polib
        po = polib.pofile(source_po, encoding="utf-8")
        original_count = len(po)

        # load system msgids if not yet cached
        if domain not in self._all_system_msgids:
            self._load_all_system_msgids(self.lang, domain)
        system_msgids = self._all_system_msgids.get(domain, set())

        # --- self dedupe + system dedupe ---
        seen_msgids = set()
        new_entries = []

        header_entry = None
        for entry in po:
            if entry.msgid == "":
                header_entry = entry
                continue
            if entry.msgid in seen_msgids:
                continue
            if entry.msgid in system_msgids:
                continue
            seen_msgids.add(entry.msgid)
            new_entries.append(entry)

        # restore header at top
        if header_entry:
            new_entries.insert(0, header_entry)

        removed_count = original_count - len(new_entries)
        modified = removed_count > 0

        if not modified:
            self._emit_progress({"event": "nochange", "file": source_po})
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
        if self.backup:
            backup_path = self._make_backup(source_po)
            backup_created = True

        # --- overwrite entries safely ---
        po.clear()  # clear all
        for e in new_entries:
            po.append(e)
        po.save(source_po)

        self._emit_progress({
            "event": "modified",
            "file": source_po,
            "removed": removed_count,
            "backup": backup_path if backup_created else ""
        })

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
        if self.domain is None:
            domains = self.DOMAIN
        elif self.domain in self.DOMAIN:
            domains = (self.domain,)
        else:
            raise ValueError(f"Invalid domain: {self.domain}")

        results = []

        for d in domains:
            # load sys entries
            self._load_all_system_msgids(self.lang, d)

            # source list
            source_files = self._get_source_files(self.lang, d)

            self._emit_progress({
                "event": "domain_start",
                "domain": d,
                "count": len(source_files),
            })

            for src in source_files:
                try:
                    result = self.process_one(src, d)
                    results.append(result)
                except Exception as e:
                    self._emit_progress({
                        "event": "error",
                        "file": src,
                        "error": str(e)
                    })
                    continue

            self._emit_progress({
                "event": "domain_done",
                "domain": d,
            })

        return results


# ---------------
# CLI main entry
# ---------------
def main():
    parser = argparse.ArgumentParser(description="PO File Deduplication Tool for Django Projects")
    parser.add_argument("--lang", default="zh_Hans", help="Language code (default zh_Hans)")
    parser.add_argument("-d", "--domain", choices=["django", "djangojs"], help="Limit to specific domain")
    parser.add_argument("--no-backup", action="store_true", help="Do not create backup before cleaning")
    parser.add_argument("--no-comments", action="store_true", help="Do not preserve comments")

    args = parser.parse_args()

    # callback for CLI output
    def progress(event):
        ev = event.get("event")
        match ev:
            case "processing":
                Console.info(f"Processing: {event['file']}")
            case "nochange":
                Console.info(f"No changes: {event['file']}")
            case "modified":
                Console.success(f"Modified: {event['file']} (backup: {event.get('backup')})")
            case "domain_start":
                Console.info(f"Domain {event['domain']} - {event['count']} file(s)")
            case "domain_done":
                Console.success(f"Domain {event['domain']} done.")
            case "error":
                Console.error(f"File failed: {event['file']} -> {event['error']}")
            case _:
                Console.warning(f"Unknown event: {ev}")

    try:
        Console.info(f"Language: {args.lang}")

        deduper = PoDeduplicator(
            lang=args.lang,
            domain=args.domain,
            backup=not args.no_backup,
            keep_comments=not args.no_comments,
            progress_callback=progress,
        )

        deduper.handle()

        Console.success("Deduplication completed successfully.")
    except Exception as e:
        Console.error(f"An error has occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
