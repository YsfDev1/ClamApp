#!/usr/bin/env python3
"""
init_local_storage.py — XDG-aware first-run initializer for ClamApp.

Run once (or via the app's first-launch hook) to create all necessary
directories and a default app_data.json in the appropriate XDG location.

Priority:
  1. $XDG_DATA_HOME/clamapp          (usually ~/.local/share/clamapp)
  2. $XDG_CONFIG_HOME/clamapp        (usually ~/.config/clamapp)
  Quarantine always lives in $XDG_DATA_HOME/clamapp/quarantine (never in repo).

Usage:
    python scripts/init_local_storage.py
    # or, imported by the app at startup:
    from scripts.init_local_storage import init_storage
    data_dir = init_storage()
"""

import os
import json
import sys

# ── XDG base directories (with fallbacks) ─────────────────────────────────
XDG_DATA_HOME = os.environ.get(
    "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
)
XDG_CONFIG_HOME = os.environ.get(
    "XDG_CONFIG_HOME", os.path.expanduser("~/.config")
)

APP_NAME = "clamapp"
DATA_DIR = os.path.join(XDG_DATA_HOME, APP_NAME)
CONFIG_DIR = os.path.join(XDG_CONFIG_HOME, APP_NAME)
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")
APP_DATA_FILE = os.path.join(DATA_DIR, "app_data.json")

_DEFAULT_DATA = {
    "stats": {"total_scans": 0, "threats_found": 0, "objects_scanned": 0},
    "quarantine": [],
    "scan_history": [],
    "settings": {"language": "en", "theme": "dark"},
}


def init_storage() -> dict:
    """
    Create XDG directories and default app_data.json if they don't exist.

    Returns a dict with the resolved paths::

        {
            "data_dir": str,
            "config_dir": str,
            "quarantine_dir": str,
            "app_data_file": str,
        }
    """
    paths = {
        "data_dir": DATA_DIR,
        "config_dir": CONFIG_DIR,
        "quarantine_dir": QUARANTINE_DIR,
        "app_data_file": APP_DATA_FILE,
    }

    for directory in (DATA_DIR, CONFIG_DIR, QUARANTINE_DIR):
        os.makedirs(directory, mode=0o700, exist_ok=True)

    if not os.path.exists(APP_DATA_FILE):
        try:
            with open(APP_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(_DEFAULT_DATA, f, indent=4, ensure_ascii=False)
            os.chmod(APP_DATA_FILE, 0o600)
        except OSError as exc:
            print(f"[init_storage] WARNING: could not write {APP_DATA_FILE}: {exc}",
                  file=sys.stderr)

    return paths


if __name__ == "__main__":
    result = init_storage()
    print("ClamApp local storage initialized:")
    for key, path in result.items():
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"  [{exists}] {key}: {path}")
