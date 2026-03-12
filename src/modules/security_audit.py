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

    def _calculate_score(self, results):
        score = 100
        if not results["ufw"]:
            score -= 30
        if results["ssh"]:
            score -= 20 # Open SSH is a risk factor if not managed
        
        days = results["last_scan"]
        if days > 30:
            score -= 30
        elif days > 7:
            score -= 15
            
        return max(0, score)
