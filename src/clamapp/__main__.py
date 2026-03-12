#!/usr/bin/env python3
"""clamapp.__main__ — allows `python -m clamapp` and the `clamapp` entry-point."""
import sys
import os

# When installed as a package src/ is on the path; when run from the repo root we add it.
_src = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if _src not in sys.path:
    sys.path.insert(0, _src)

from gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ClamApp")
    window = MainWindow()
    window.setMinimumSize(400, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
