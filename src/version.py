"""
version.py — Single source of truth for ClamApp's semantic version.

Bump this file and tag the Git commit when releasing:
    git tag -a v0.1.0 -m "Release v0.1.0"
    git push origin v0.1.0
"""

__version__ = "0.1.0"
__version_info__ = (0, 1, 0)
__app_name__ = "ClamApp"
__author__ = "ClamApp Contributors"
__license__ = "GPL-3.0-or-later"

# GitHub Releases API endpoint — used by the update checker
_RELEASES_API = "https://api.github.com/repos/YOUR_USERNAME/ClamApp/releases/latest"
_RELEASES_PAGE = "https://github.com/YOUR_USERNAME/ClamApp/releases"


def check_for_updates() -> dict:
    """
    Placeholder update checker. Queries the GitHub Releases API and compares
    the latest published tag against __version__.

    Returns a dict::

        {
            "up_to_date": bool,
            "latest": str,           # e.g. "0.2.0"
            "url": str,              # Releases page
            "error": str | None,     # None when successful
        }

    Replace YOUR_USERNAME in _RELEASES_API before publishing.
    """
    import urllib.request
    import json

    try:
        req = urllib.request.Request(
            _RELEASES_API,
            headers={"User-Agent": f"{__app_name__}/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        tag = data.get("tag_name", "").lstrip("v")
        up_to_date = _version_tuple(tag) <= __version_info__
        return {
            "up_to_date": up_to_date,
            "latest": tag,
            "url": _RELEASES_PAGE,
            "error": None,
        }
    except Exception as exc:
        return {
            "up_to_date": True,   # Don't nag user if network is unavailable
            "latest": __version__,
            "url": _RELEASES_PAGE,
            "error": str(exc),
        }


def _version_tuple(version_str: str) -> tuple:
    """Convert '1.2.3' → (1, 2, 3). Non-numeric components become 0."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except ValueError:
        return (0, 0, 0)


if __name__ == "__main__":
    from utils.logger import get_logger
    logger = get_logger("Version")
    
    logger.info(f"{__app_name__} v{__version__}")
    result = check_for_updates()
    if result["error"]:
        logger.error(f"Update check failed: {result['error']}")
    elif result["up_to_date"]:
        logger.info("You are running the latest version.")
    else:
        logger.info(f"Update available: v{result['latest']} — {result['url']}")
