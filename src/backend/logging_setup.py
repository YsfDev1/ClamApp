"""
logging_setup.py — Centralized logging configuration for ClamApp.
Writes to ~/.config/clamapp/logs/clamapp.log (rotating, max 2 MB × 3).
Silent in the console; pass --debug flag to enable verbose output.
"""

import logging
import logging.handlers
import os
import sys


def setup_logging() -> None:
    """Call once at application startup before creating the QApplication."""
    log_dir = os.path.expanduser("~/.config/clamapp/logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "clamapp.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # ── Rotating file handler (always active) ─────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(fh)

    # ── Console handler (only in --debug mode) ────────────────────────────
    if "--debug" in sys.argv:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
        root_logger.addHandler(ch)

    logging.getLogger(__name__).info("ClamApp logging initialised → %s", log_file)
