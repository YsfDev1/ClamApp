import json
import os
import logging
import base64
import secrets
import re

log = logging.getLogger(__name__)

class SettingsManager:
    _SENSITIVE_KEYS = {"vt_api_key", "hibp_api_key", "bd_api_key"}
    _ENC_PREFIX = "enc:"

    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/clamapp")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self._ensure_config_dir()
        self.config = self.load_config()

    def _ensure_config_dir(self):
        os.makedirs(self.config_dir, exist_ok=True)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                # Merge missing defaults without overwriting existing values
                defaults = self._defaults()
                for k, v in defaults.items():
                    data.setdefault(k, v)
                # Ensure local obfuscation key exists
                if not data.get("_local_obf_key"):
                    data["_local_obf_key"] = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii")
                # Migrate plaintext sensitive values to obfuscated form
                migrated = False
                for sk in self._SENSITIVE_KEYS:
                    val = data.get(sk, "")
                    if isinstance(val, str) and val and not val.startswith(self._ENC_PREFIX):
                        data[sk] = self._obfuscate(val, data["_local_obf_key"])
                        migrated = True
                if migrated:
                    try:
                        with open(self.config_file, "w") as wf:
                            json.dump(data, wf, indent=4)
                    except Exception:
                        pass
                return data
            except Exception as e:
                log.error("Error loading config: %s", e)

        return self._defaults()

    def _defaults(self) -> dict:
        return {
            "vt_api_key": "",
            "hibp_api_key": "",
            "bd_api_key": "",
            "breach_provider": "bd",  # "bd" | "hibp"
            "daily_scan_enabled": False,
            "scan_time": "03:00",
            "first_run_done": False,
            "_local_obf_key": base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii"),
        }

    def save_config(self, config_data=None):
        if config_data:
            self.config.update(config_data)

        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            log.error("Error saving config: %s", e)
            return False

    def get(self, key, default=None):
        val = self.config.get(key, default)
        if key in self._SENSITIVE_KEYS and isinstance(val, str) and val.startswith(self._ENC_PREFIX):
            try:
                return self._deobfuscate(val, self.config.get("_local_obf_key", "")) or ""
            except Exception:
                return ""
        return val

    def set(self, key, value):
        if key in self._SENSITIVE_KEYS:
            raw = (value or "").strip()
            ok, msg = self._validate_key_format(key, raw)
            if not ok:
                log.warning("Rejected %s: %s", key, msg)
                # Keep existing value if invalid
                return False, msg
            self.config[key] = self._obfuscate(raw, self.config.get("_local_obf_key", ""))
        else:
            self.config[key] = value
        return self.save_config(), ""

    def _validate_key_format(self, key: str, value: str) -> tuple[bool, str]:
        if not value:
            return True, ""
        if key == "vt_api_key":
            # VT keys are typically 64 hex chars
            if not re.fullmatch(r"[A-Fa-f0-9]{64}", value):
                return False, "Invalid VirusTotal API key format."
        if key == "hibp_api_key":
            # HIBP keys are not strictly documented as a pattern; enforce sane length.
            if len(value) < 12:
                return False, "Invalid HIBP API key format."
        if key == "bd_api_key":
            # RapidAPI keys are long tokens; enforce sane length.
            if len(value) < 16:
                return False, "Invalid BreachDirectory API key format."
        return True, ""

    def _obfuscate(self, plaintext: str, key_b64: str) -> str:
        if plaintext == "":
            return ""
        try:
            key = base64.urlsafe_b64decode((key_b64 or "").encode("ascii"))
        except Exception:
            key = secrets.token_bytes(24)
            self.config["_local_obf_key"] = base64.urlsafe_b64encode(key).decode("ascii")
        data = plaintext.encode("utf-8")
        xored = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        return self._ENC_PREFIX + base64.urlsafe_b64encode(xored).decode("ascii")

    def _deobfuscate(self, encoded: str, key_b64: str) -> str:
        if not encoded or not encoded.startswith(self._ENC_PREFIX):
            return encoded or ""
        payload = encoded[len(self._ENC_PREFIX):]
        key = base64.urlsafe_b64decode((key_b64 or "").encode("ascii"))
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = bytes([b ^ key[i % len(key)] for i, b in enumerate(blob)])
        return data.decode("utf-8", errors="replace")
