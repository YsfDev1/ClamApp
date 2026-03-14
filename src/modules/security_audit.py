import os
import subprocess
import socket
import json
from datetime import datetime

class SecurityAuditLogic:
    """
    Checks system security status and calculates a score.
    """
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def perform_audit(self):
        results = {
            "ufw": self._check_ufw(),
            "ssh": self._check_ssh_port(),
            "last_scan": self._check_last_scan(),
            "root_login": self._check_root_login(),
            "shadow_perms": self._check_file_permissions("/etc/shadow"),
            "open_ports": self._check_open_ports([21, 23, 111, 139, 445]),
        }
        score = self._calculate_score(results)
        results["score"] = score
        return results

    def _check_ufw(self):
        try:
            # Requires root or configured ufw visibility
            res = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
            return "active" in res.stdout.lower()
        except Exception:
            return False

    def _check_ssh_port(self):
        """
        Briefly checks if port 22 is listening.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                # Check local reachability
                return s.connect_ex(('127.0.0.1', 22)) == 0
        except Exception:
            return False

    def _check_last_scan(self):
        """
        Returns days since last scan.
        """
        history = self.data_manager.data.get("scan_history", [])
        if not history:
            return 999 # Long time
        
        try:
            last_date_str = history[-1].get("date", "")
            # Assuming format: "2026-03-12 10:00:00"
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - last_date
            return delta.days
        except Exception:
            return 999

    def _check_root_login(self):
        """Checks if root login is permitted in sshd_config."""
        try:
            if not os.path.exists("/etc/ssh/sshd_config"):
                return True # Assume OK if SSH not installed
            with open("/etc/ssh/sshd_config", "r") as f:
                for line in f:
                    if line.strip().startswith("PermitRootLogin") and "yes" in line.lower():
                        return False # Risky
            return True
        except Exception:
            return True

    def _check_file_permissions(self, path):
        """Checks if critical file has safe permissions (e.g. 600 or 640)."""
        try:
            if not os.path.exists(path):
                return True
            mode = os.stat(path).st_mode
            # 600 is 100600 octal, 640 is 100640 octal
            perms = oct(mode & 0o777)
            return perms in ["0o600", "0o640", "0o400", "0o000"]
        except Exception:
            return False

    def _check_open_ports(self, ports):
        """Scans for open ports using sockets."""
        open_ports = []
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    if s.connect_ex(('127.0.0.1', port)) == 0:
                        open_ports.append(port)
            except Exception:
                continue
        return open_ports

    def _calculate_score(self, results):
        score = 100
        if not results["ufw"]:
            score -= 20
        if results["ssh"]:
            score -= 10
        if not results["root_login"]:
            score -= 15
        if not results["shadow_perms"]:
            score -= 15
        if results["open_ports"]:
            score -= 10 * len(results["open_ports"])
        
        days = results["last_scan"]
        if days > 30:
            score -= 20
        elif days > 7:
            score -= 10
            
        return max(0, score)
