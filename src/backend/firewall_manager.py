"""
firewall_manager.py — UFW firewall backend for ClamApp.

Enterprise-grade, GUI-friendly wrapper around UFW with:
- absolute-path execution preference (/usr/sbin/ufw)
- robust status + numbered rule parsing
- privileged actions via pkexec
"""

import subprocess
import shutil
import re
import logging
import os

log = logging.getLogger(__name__)


class FirewallManagerBackend:
    """Backend logic for UFW firewall management."""

    UFW_ABS_PATH = "/usr/sbin/ufw"
    UFW_FALLBACK_PATH = "/sbin/ufw"

    PROFILES = {
        # Simple mode profiles
        "home": [
            ("default", ["deny", "incoming"]),
            ("default", ["allow", "outgoing"]),
        ],
        "public": [
            ("default", ["deny", "incoming"]),
            ("default", ["allow", "outgoing"]),
            # Best-effort ICMP stealth: drop inbound ping (rule may fail on some ufw versions)
            ("rule", ["deny", "in", "proto", "icmp"]),
            ("rule", ["deny", "in", "proto", "icmpv6"]),
        ],
        "kill": [
            ("default", ["deny", "incoming"]),
            ("default", ["deny", "outgoing"]),
        ],
    }

    def is_ufw_installed(self) -> bool:
        if os.path.exists(self.UFW_ABS_PATH) or os.path.exists(self.UFW_FALLBACK_PATH):
            return True
        return shutil.which("ufw") is not None

    def ufw_path(self) -> str:
        if os.path.exists(self.UFW_ABS_PATH):
            return self.UFW_ABS_PATH
        if os.path.exists(self.UFW_FALLBACK_PATH):
            return self.UFW_FALLBACK_PATH
        return "ufw"

    def _pkexec(self, *args: str) -> list:
        return ["pkexec", self.ufw_path(), *args]

    def get_status(self) -> dict:
        """
        Returns:
            {
                "installed": bool,
                "enabled": bool,
                "rules": [str],   # list of active rule lines
                "error": str | None,
            }
        """
        if not self.is_ufw_installed():
            return {"installed": False, "enabled": False, "rules": [], "error": "UFW is not installed."}

        output = ""

        # Try pkexec first for consistent GUI experience.
        # Polkit policy (com.clamapp.ufw.policy) will handle auth caching.
        for cmd in [
            [self.ufw_path(), "status", "verbose"], # Try unprivileged first
            self._pkexec("status", "verbose"),
        ]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                combined = (result.stdout or "") + (result.stderr or "")
                if "Status:" in combined:
                    output = combined
                    break
            except Exception as exc:
                log.debug("UFW status attempt failed: %s", exc)
                continue

        if not output:
            return {"installed": True, "enabled": False, "rules": [], 
                    "error": "Permission denied reading UFW status."}

        enabled = "Status: active" in output
        rules = self._parse_rules(output)
        logging_on = self._parse_logging_enabled(output)
        return {"installed": True, "enabled": enabled, "rules": rules, "logging": logging_on, "error": None}

    def get_rules_numbered(self) -> dict:
        """Return structured rules from `ufw status numbered`."""
        if not self.is_ufw_installed():
            return {"success": False, "rules": [], "message": "UFW is not installed."}

        for cmd in [
            [self.ufw_path(), "status", "numbered"],
            self._pkexec("status", "numbered"),
        ]:
            res = self._run_maybe_privileged(cmd)
            if res["success"] and res.get("message"):
                return {"success": True, "rules": self._parse_numbered_rules(res["message"]), "message": ""}
        return {"success": False, "rules": [], "message": "Authorization failed."}

    def is_logging_enabled(self) -> dict:
        st = self.get_status()
        if not st.get("installed"):
            return {"success": False, "enabled": False, "message": st.get("error", "")}
        if st.get("error"):
            return {"success": False, "enabled": bool(st.get("logging")), "message": st.get("error", "")}
        return {"success": True, "enabled": bool(st.get("logging")), "message": ""}

    def ensure_logging_enabled(self) -> dict:
        """Enable UFW logging if not already enabled (best-effort)."""
        chk = self.is_logging_enabled()
        if chk.get("success") and chk.get("enabled"):
            return {"success": True, "message": "Already enabled."}
        return self.enable_logging(True)

    def enable_logging(self, enabled: bool) -> dict:
        if not self.is_ufw_installed():
            return {"success": False, "message": "UFW is not installed."}
        cmd = self._pkexec("logging", "on" if enabled else "off")
        return self._run_privileged(cmd)

    def set_enabled(self, enabled: bool) -> dict:
        """Enable or disable the firewall. Returns {"success": bool, "message": str}."""
        if not self.is_ufw_installed():
            return {"success": False, "message": "UFW is not installed."}

        cmd = self._pkexec("--force", "enable" if enabled else "disable")
        result = self._run_privileged(cmd)
        if result["success"]:
            log.info("UFW %s successfully.", "enabled" if enabled else "disabled")
        else:
            log.warning("UFW toggle failed: %s", result["message"])
        return result

    def apply_profile(self, profile_name: str) -> dict:
        """Apply a preset profile. Returns {"success": bool, "message": str}."""
        if not self.is_ufw_installed():
            return {"success": False, "message": "UFW is not installed."}
        actions = self.PROFILES.get(profile_name, [])
        if not actions:
            return {"success": False, "message": f"Unknown profile: {profile_name}"}

        # Reset first, then apply the profile
        reset_result = self._run_privileged(self._pkexec("--force", "reset"))
        if not reset_result["success"]:
            return reset_result

        errors = []
        for kind, argv in actions:
            if kind == "default":
                parts = self._pkexec("default", *argv)
            else:
                parts = self._pkexec(*argv)
            r = self._run_privileged(parts)
            if not r["success"]:
                errors.append(r["message"])
                log.warning("UFW profile action failed: %s — %s", parts, r["message"])

        # Re-enable after applying rules
        self._run_privileged(self._pkexec("--force", "enable"))

        if errors:
            return {"success": False, "message": "Some rules failed:\n" + "\n".join(errors)}
        log.info("UFW profile '%s' applied.", profile_name)
        return {"success": True, "message": f"Profile '{profile_name}' applied successfully."}

    def delete_rule(self, rule_id: int) -> dict:
        if not self.is_ufw_installed():
            return {"success": False, "message": "UFW is not installed."}
        cmd = self._pkexec("--force", "delete", str(rule_id))
        return self._run_privileged(cmd)

    def add_rule(self, action: str, direction: str, port: str, protocol: str) -> dict:
        """
        action: allow|deny|reject
        direction: in|out
        protocol: any|tcp|udp
        port: "22" or "ssh" or "80,443" etc (passed as-is to ufw)
        """
        if not self.is_ufw_installed():
            return {"success": False, "message": "UFW is not installed."}

        action = (action or "").lower()
        direction = (direction or "").lower()
        protocol = (protocol or "").lower()

        if action not in {"allow", "deny", "reject"}:
            return {"success": False, "message": "Invalid action."}
        if direction not in {"in", "out"}:
            return {"success": False, "message": "Invalid direction."}
        if protocol not in {"any", "tcp", "udp"}:
            return {"success": False, "message": "Invalid protocol."}
        if not port:
            return {"success": False, "message": "Port/service is required."}

        spec = port if protocol == "any" else f"{port}/{protocol}"
        cmd = self._pkexec(action, direction, spec)
        return self._run_privileged(cmd)

    def _run_privileged(self, cmd: list) -> dict:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return {"success": True, "message": result.stdout.strip()}
            else:
                err = result.stderr.strip() or result.stdout.strip()
                return {"success": False, "message": err or "Command failed."}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Operation timed out. Check sudo permissions."}
        except FileNotFoundError:
            return {"success": False, "message": "pkexec not found. Cannot elevate privileges."}
        except Exception as e:
            log.error("Privileged command error: %s", e)
            return {"success": False, "message": str(e)}

    def _run_maybe_privileged(self, cmd: list) -> dict:
        """
        Runs either an unprivileged command or a pkexec command.
        If cmd starts with 'pkexec' we treat it as privileged.
        """
        if cmd and cmd[0] == "pkexec":
            return self._run_privileged(cmd)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"success": True, "message": (result.stdout or "").strip()}
            err = (result.stderr or "").strip() or (result.stdout or "").strip()
            return {"success": False, "message": err or "Command failed."}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def _parse_rules(self, output: str) -> list:
        """Extract active rule lines from ufw verbose output."""
        rules = []
        in_rules = False
        for line in output.splitlines():
            if line.startswith("--"):
                in_rules = True
                continue
            if in_rules and line.strip():
                rules.append(line.strip())
        return rules

    def _parse_logging_enabled(self, output: str) -> bool:
        for line in (output or "").splitlines():
            if line.strip().lower().startswith("logging:"):
                return "on" in line.lower()
        return False

    def _parse_numbered_rules(self, output: str) -> list[dict]:
        """
        Parse `ufw status numbered` output.
        Typical line:
          [ 1] 22/tcp                     ALLOW IN    Anywhere
          [ 2] 80/tcp                     ALLOW IN    Anywhere (v6)
        """
        rules = []
        for line in (output or "").splitlines():
            m = re.match(r"^\[\s*(\d+)\]\s+(.+?)\s{2,}(\w+)\s+(IN|OUT)\s+(.*)$", line.strip())
            if not m:
                continue
            rule_id = int(m.group(1))
            port_service = m.group(2).strip()
            action = m.group(3).strip().upper()
            direction = m.group(4).strip().upper()
            rest = m.group(5).strip()

            proto = "Any"
            ps = port_service
            if "/" in port_service:
                ps, p = port_service.rsplit("/", 1)
                proto = p.upper()

            rules.append({
                "id": rule_id,
                "action": action.capitalize(),
                "direction": "In" if direction == "IN" else "Out",
                "port_service": ps.strip(),
                "protocol": proto,
                "raw": line.strip(),
                "target": rest,
            })
        return rules
