#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO file tool

Description:
  This tool cleans project-level .po files by removing entries already included
  in Django’s built-in translations or in the cmfadmin application. It helps
  maintain minimal, non-duplicated translation files for each app.

  Features:
    - Removes duplicate or redundant translation entries
    - Subtracts entries existing in system PO files (Django + cmfadmin)
    - Preserves file metadata and optionally developer comments
    - Automatically creates a backup unless disabled

  Notes:
    - If no valid diff PO files are found, cleaning continues with system defaults
    - The source file must exist; otherwise, the process aborts immediately
    - Missing system PO files are silently ignored
    - Works both as a CLI command and a Python utility

  CLI Usage:
    python po_tool.py [source_po] [options]

  Examples:
    # Clean a PO file using default Django + cmfadmin references
    python po_tool.py locale/zh_Hans/LC_MESSAGES/django.po

    # Specify custom diff PO files explicitly
    python po_tool.py source.po --diff django.po cmfadmin.po --lang zh_Hans

    # Auto-detect PO file by app name, skip backup
    python po_tool.py --app blog --lang zh_Hans --no-backup

  Arguments:
    source_po         Path to the source PO file to clean

  Options:
    --diff <files...> Optional list of diff PO files for exclusion
    --app <app>       Django app name for locating its PO file automatically
    --lang <lang>     Language code for default PO paths (default: zh_Hans)
    --no-backup       Disable automatic backup before cleaning
    --no-comments     Remove all developer comments from the output file

  Programmatic Usage:
    from cmfadmin.utils.po_tool import PoTool

    result = PoTool.clean(
        source_po="path/to/source.po",
        diff_po_list=["path/to/django.po", "path/to/cmfadmin.po"],
        lang="zh_Hans",
        backup=True
    )

    print(f"Removed {result['removed_count']} entries, kept {result['remaining_count']}")

  Return Values:
    Returns a dict with:
        processed_count:   Total entries processed
        removed_count:     Number of entries removed
        remaining_count:   Number of entries kept
        diff_files_used:   Diff PO files successfully processed
        backup_path:       Path of backup file (if created)
        backup_created:    True if a backup was made

  Error Handling:
    - Raises FileNotFoundError if the source file is missing
    - Raises IOError or PermissionError if backup or save fails
    - Invalid PO files will abort the process immediately

Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-05
"""

import argparse
import datetime
import os
import site
import sys
from pathlib import Path

# Add project root to Python path
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
        raise ImportError("polib is required for po_clean to function.")


class PoTool:
    """Core PO cleaning logic."""

    @staticmethod
    def _get_source_po(source_po: str | None, app: str = "", lang: str = "zh_Hans") -> str | None:
        """Return valid source PO path or None."""
        if source_po:
            if not os.path.exists(source_po):
                raise FileNotFoundError(f"Source PO file not found: {source_po}")
            return source_po

        # Try auto path
        path = os.path.join(os.getcwd(), app, "locale", lang, "LC_MESSAGES", "django.po")
        return path if os.path.exists(path) else None

    @staticmethod
    def _get_default_diff_files(lang: str) -> list[str]:
        """Generate list of default system PO files (Django + cmfadmin)."""
        base_paths = site.getsitepackages()
        packages = ["django/conf", "django/contrib/admin", "django/contrib/auth", "cmfadmin"]

        paths: list[str] = []
        for base in base_paths:
            for pkg in packages:
                full_path = os.path.join(base, pkg, "locale", lang, "LC_MESSAGES", "django.po")
                if os.path.exists(full_path):
                    paths.append(full_path)
        return paths

    @staticmethod
    def _get_diff_po(lang: str, diff_po_list: str | list[str] | None) -> list[str]:
        """Validate user-specified diff files and merge with system ones."""
        valid_files: list[str] = []

        # Validate user-provided diff files (must exist)
        if diff_po_list:
            if isinstance(diff_po_list, str):
                diff_po_list = [diff_po_list]

            missing = [f for f in diff_po_list if not os.path.exists(f)]
            if missing:
                raise FileNotFoundError(f"Diff files not found: {', '.join(missing)}")
            valid_files.extend(diff_po_list)

        # Append system diff files (silently skip missing)
        system_files = PoTool._get_default_diff_files(lang)
        valid_files.extend([f for f in system_files if os.path.exists(f)])

        return valid_files

    @staticmethod
    def _make_backup(file_path: str) -> str:
        """Create timestamped backup of the source file."""
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_{timestamp}.bak"
        with open(file_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
        return backup_path

    @classmethod
    def clean(cls,
              source_po: str | None = None,
              diff_po_list: str | list[str] | None = None,
              app: str = "",
              lang: str = "zh_Hans",
              backup: bool = True,
              keep_comments: bool = True,
              ) -> dict:
        """Main cleaning logic callable from other programs."""
        result = {
            "processed_count": 0,
            "removed_count": 0,
            "remaining_count": 0,
            "diff_files_used": [],
            "backup_path": "",
            "backup_created": False,
        }

        # Step 1: Locate source file
        source_path = cls._get_source_po(source_po, app, lang)
        if not source_path:
            raise FileNotFoundError("No valid source PO file found.")

        # Step 2: Get diff PO files
        diff_files = cls._get_diff_po(lang, diff_po_list)
        result["diff_files_used"] = diff_files

        # Step 3: Load source
        po = polib.pofile(source_path)
        result["processed_count"] = len(po)

        # Step 4: Deduplicate (keep first occurrence)
        seen = set()
        unique_entries = []
        for entry in po:
            if entry.msgid not in seen:
                seen.add(entry.msgid)
                unique_entries.append(entry)
        po._entries = {e.msgid: e for e in unique_entries}

        # Step 5: Remove entries already in diff files
        diff_msgids = set()
        for diff_file in diff_files:
            diff_po = polib.pofile(diff_file)
            diff_msgids.update(e.msgid for e in diff_po)

        to_remove = [e for e in po if e.msgid in diff_msgids and e.msgid]
        for e in to_remove:
            po.remove(e)

        result["removed_count"] = len(to_remove)
        result["remaining_count"] = len(po)

        # Step 6: Backup
        if backup:
            result["backup_path"] = cls._make_backup(source_path)
            result["backup_created"] = True

        # Step 7: Write cleaned file
        # Preserve metadata but remove the empty msgid entry (header handled separately)
        if not keep_comments:
            for entry in po:
                entry.comment = ""

        po.save(source_path)

        return result


# --------------------------- CLI Entry --------------------------- #

def main():
    parser = argparse.ArgumentParser(description="PO file cleaner with internal deduplication.")
    parser.add_argument("source_po", nargs="?", help="Source PO file path")
    parser.add_argument("--diff", nargs="+", help="Diff PO files for exclusion")
    parser.add_argument("--app", help="App name to locate standard PO file")
    parser.add_argument("--lang", default="zh_Hans", help="Language code (default zh_Hans)")
    parser.add_argument("--no-backup", action="store_true", help="Do not create backup before cleaning")
    parser.add_argument("--no-comments", action="store_true", help="Do not preserve comments")

    args = parser.parse_args()

    backup = not args.no_backup
    keep_comments = not args.no_comments

    try:
        Console.info(f"Source: {args.source_po or '(auto-detect)'}")
        Console.info(f"Language: {args.lang}")
        Console.info(f"Collecting diff files...")

        result = PoTool.clean(
            source_po=args.source_po,
            diff_po_list=args.diff,
            app=args.app or "",
            lang=args.lang,
            backup=backup,
            keep_comments=keep_comments,
        )

        Console.info(f"Using {len(result['diff_files_used'])} diff files.")
        if result["backup_created"]:
            Console.success("Backup created successfully.")
        Console.info(f"Processed: {result['processed_count']}, Removed: {result['removed_count']}, Remaining: {result['remaining_count']}")
        Console.success("Cleaning completed successfully.")

    except (FileNotFoundError, ImportError) as e:
        Console.error(f"{e}")
        sys.exit(1)
    except Exception as e:
        Console.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
