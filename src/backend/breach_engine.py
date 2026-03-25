"""
breach_engine.py — provider-agnostic breach checking bridge for ClamApp.

Supports:
- BreachDirectory (RapidAPI) (Free / Recommended)
- Have I Been Pwned (HIBP) v3 (Subscription)
"""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
import urllib.error


class BreachEngine:
    PROVIDER_BD = "bd"
    PROVIDER_HIBP = "hibp"

    HIBP_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"
    HIBP_USER_AGENT = "ClamApp-SecuritySuite/1.0"

    # Common RapidAPI endpoint used for BreachDirectory.
    # Kept as constants so it can be adjusted without touching UI code.
    BD_RAPIDAPI_URL = "https://breachdirectory.p.rapidapi.com/"
    BD_RAPIDAPI_HOST = "breachdirectory.p.rapidapi.com"

    def check_email(self, email: str, provider: str, api_key: str) -> dict:
        provider = (provider or "").lower().strip()
        if provider == self.PROVIDER_HIBP:
            return self._check_hibp(email, api_key)
        return self._check_bd(email, api_key)

    def _check_hibp(self, email: str, api_key: str) -> dict:
        if not api_key:
            return {"status": "no_key", "breaches": [], "message": "no_key"}

        url = self.HIBP_BREACHES_URL.format(email=urllib.parse.quote(email))
        req = urllib.request.Request(url)
        req.add_header("User-Agent", self.HIBP_USER_AGENT)
        req.add_header("Accept", "application/json")
        req.add_header("hibp-api-key", api_key)

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                breaches = []
                for b in data:
                    breaches.append({
                        "title": b.get("Title", "Unknown"),
                        "date": b.get("BreachDate") or "",
                    })
                return {"status": "breached", "breaches": breaches, "message": "breached"}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"status": "safe", "breaches": [], "message": "safe"}
            if e.code == 401:
                return {"status": "error", "breaches": [], "message": "invalid_key", "http": 401}
            if e.code == 429:
                return {"status": "error", "breaches": [], "message": "rate_limited", "http": 429}
            return {"status": "error", "breaches": [], "message": "http_error", "http": e.code}
        except urllib.error.URLError:
            return {"status": "error", "breaches": [], "message": "network_error"}
        except Exception:
            return {"status": "error", "breaches": [], "message": "unexpected_error"}

    def _check_bd(self, email: str, api_key: str) -> dict:
        if not api_key:
            return {"status": "no_key", "breaches": [], "message": "no_key"}

        query = urllib.parse.urlencode({"func": "auto", "term": email})
        url = self.BD_RAPIDAPI_URL + "?" + query
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/json")
        req.add_header("X-RapidAPI-Key", api_key)
        req.add_header("X-RapidAPI-Host", self.BD_RAPIDAPI_HOST)

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                breaches = self._parse_bd_response(data)
                if not breaches:
                    return {"status": "safe", "breaches": [], "message": "safe"}
                return {"status": "breached", "breaches": breaches, "message": "breached"}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"status": "safe", "breaches": [], "message": "safe"}
            if e.code == 401:
                return {"status": "error", "breaches": [], "message": "invalid_key", "http": 401}
            if e.code == 429:
                return {"status": "error", "breaches": [], "message": "rate_limited", "http": 429}
            return {"status": "error", "breaches": [], "message": "http_error", "http": e.code}
        except urllib.error.URLError:
            return {"status": "error", "breaches": [], "message": "network_error"}
        except Exception:
            return {"status": "error", "breaches": [], "message": "unexpected_error"}

    def _parse_bd_response(self, data) -> list[dict]:
        """
        BD responses vary by provider/package. We support a few common shapes:
        - dict with "sources": [..]
        - dict with "result": {"sources":[..]} or list entries
        - list of records [{title/domain/created}, ...]
        """
        sources = []

        if isinstance(data, dict):
            if isinstance(data.get("sources"), list):
                sources = data.get("sources")
            elif isinstance(data.get("result"), dict) and isinstance(data["result"].get("sources"), list):
                sources = data["result"]["sources"]
            elif isinstance(data.get("result"), list):
                # Some APIs return a list of records under result; treat title/domain as sources
                for r in data.get("result", []):
                    if isinstance(r, dict):
                        s = r.get("title") or r.get("domain") or r.get("source")
                        if s:
                            sources.append(s)
        elif isinstance(data, list):
            for r in data:
                if isinstance(r, dict):
                    s = r.get("title") or r.get("domain") or r.get("source")
                    if s:
                        sources.append(s)

        # Normalize + dedupe preserving order
        seen = set()
        out = []
        for s in sources:
            if not isinstance(s, str):
                continue
            name = s.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            out.append({"title": name, "date": ""})
        return out

