"""
setup.py — legacy compatibility shim for cross-distro pip installs.

Most packaging is declared in pyproject.toml.  This file exists so that
older pip versions (< 21.3) and system package managers on Debian/Ubuntu/
Fedora/Arch that call `python setup.py install` still work correctly.
"""

from setuptools import setup

# All real metadata lives in pyproject.toml.
# This call is intentionally minimal.
setup()
