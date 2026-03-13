"""
DataManager — persistent storage and secure quarantine for ClamApp.

Secure quarantine changes (vs original):
  - Quarantine dir moved to ~/.clamapp/quarantine/ (expanduser, not project dir).
  - secure_quarantine(): moves file, chmod 0o000, writes per-item metadata.json.
  - restore_file(): restores permissions to 0o600 and removes metadata.json sidecar.
  - delete_permanently(): also removes metadata.json sidecar.
  - All I/O wrapped in try/except returning (success: bool, message: str).
"""

import json
import os
import shutil
from datetime import datetime


class DataManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir

        # Use ~/.clamapp/quarantine/ for Pardus/Linux compatibility
        self.quarantine_dir = os.path.expanduser("~/.clamapp/quarantine")

        try:
            os.makedirs(self.quarantine_dir, exist_ok=True)
        except OSError as exc:
            print(f"[DataManager] Could not create quarantine dir: {exc}")

        # Legacy path used by earlier builds — keep reference for migration
        self._legacy_quarantine_dir = os.path.join(base_dir, "quarantine")

        self.data_file = os.path.join(base_dir, "app_data.json")
        self.data = self.load_data()

    # ── Persistence ────────────────────────────────────────────────────────

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Ensure required keys exist
                data.setdefault("stats", {"total_scans": 0, "threats_found": 0, "objects_scanned": 0})
                data.setdefault("quarantine", [])
                data.setdefault("scan_history", [])
                data.setdefault("settings", {"language": "en"})
                data["settings"].setdefault("theme", "dark")

                # Migration: add missing IDs to old records
                for i, item in enumerate(data.get("quarantine", [])):
                    if "id" not in item:
                        item["id"] = f"migrated_{i}"

                self.data = data
                self.save_data()
                return data
            except Exception as exc:
                print(f"[DataManager] load_data error: {exc}")


        return {
            "stats": {"total_scans": 0, "threats_found": 0, "objects_scanned": 0},
            "quarantine": [],
            "scan_history": [],
            "settings": {"language": "en", "theme": "dark"},
        }

    def save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except (OSError, PermissionError) as exc:
            print(f"[DataManager] save_data error: {exc}")


    def add_scan_result(self, threats, objects=100, scan_type="Custom", path=""):
        self.data["stats"]["total_scans"] += 1
        self.data["stats"]["threats_found"] += threats
        self.data["stats"]["objects_scanned"] += objects


        self.data["scan_history"].insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": scan_type,
            "path": path,
            "threats": threats,
            "objects": objects,

        })
        # Keep only last 50 scans
        self.data["scan_history"] = self.data["scan_history"][:50]
        self.save_data()

    # ── Secure Quarantine ──────────────────────────────────────────────────

    def secure_quarantine(self, file_path: str) -> tuple[bool, str]:
        """
        Securely quarantine an infected file:
          1. Move to ~/.clamapp/quarantine/<timestamp>_<name>
          2. Strip all permissions with chmod 0o000 (kills malware execution)
          3. Write per-item metadata.json sidecar for future restoration
          4. Persist quarantine record in app_data.json

        Returns (success: bool, message: str).
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{filename}"
        dest_path = os.path.join(self.quarantine_dir, safe_name)
        meta_path = dest_path + ".meta.json"
        quarantine_id = f"{timestamp}_{filename}"

        try:
            shutil.move(file_path, dest_path)
        except PermissionError:
            return False, f"Permission denied moving '{filename}'. Try running as root or check file ownership."
        except OSError as exc:
            return False, f"OS error moving '{filename}': {exc}"

        # Strip all permissions to disable malware execution
        try:
            os.chmod(dest_path, 0o000)
        except (OSError, PermissionError) as exc:
            # Non-fatal: file is already moved out of its original location
            print(f"[DataManager] chmod 0o000 failed for {dest_path}: {exc}")

        # Write metadata sidecar
        meta = {
            "id": quarantine_id,
            "original_path": file_path,
            "quarantine_path": dest_path,
            "quarantine_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, indent=4, ensure_ascii=False)
        except (OSError, PermissionError) as exc:
            print(f"[DataManager] Could not write metadata sidecar: {exc}")

        # Persist in app_data.json
        self.data["quarantine"].append({
            "id": quarantine_id,
            "original_path": file_path,
            "quarantine_path": dest_path,
            "date": meta["quarantine_date"],
        })
        self.save_data()
        return True, f"'{filename}' quarantined successfully."

    # Backwards-compatible alias used by old code paths
    def quarantine_file(self, file_path: str) -> bool:
        success, _ = self.secure_quarantine(file_path)
        return success

    # ── Restore / Delete ───────────────────────────────────────────────────

    def restore_file(self, quarantine_id: str) -> tuple[bool, str]:
        """
        Restore a quarantined file back to its original path.
        Re-grants 0o600 (rw for owner) so the file becomes usable.
        Returns (success, message).
        """
        for i, item in enumerate(self.data["quarantine"]):
            if item["id"] == quarantine_id:
                q_path = item["quarantine_path"]
                orig_path = item["original_path"]

                # Re-grant read permission so we can move it
                try:
                    os.chmod(q_path, 0o600)
                except (OSError, PermissionError) as exc:
                    return False, f"Cannot restore permissions on quarantined file: {exc}"

                try:
                    # Ensure target directory exists
                    os.makedirs(os.path.dirname(orig_path) or ".", exist_ok=True)
                    shutil.move(q_path, orig_path)
                except PermissionError:
                    return False, f"Permission denied restoring to '{orig_path}'."
                except OSError as exc:
                    return False, f"OS error during restore: {exc}"

                # Remove metadata sidecar
                meta_path = q_path + ".meta.json"
                try:
                    if os.path.exists(meta_path):
                        os.remove(meta_path)
                except OSError:
                    pass

                self.data["quarantine"].pop(i)
                self.save_data()
                return True, f"File restored to '{orig_path}'."

        return False, f"Quarantine record '{quarantine_id}' not found."

    def delete_permanently(self, quarantine_id: str) -> tuple[bool, str]:
        """
        Permanently delete a quarantined file (and its metadata sidecar).
        Returns (success, message).
        """
        for i, item in enumerate(self.data["quarantine"]):
            if item["id"] == quarantine_id:
                q_path = item["quarantine_path"]

                try:
                    if os.path.exists(q_path):
                        # Temporarily grant write permission to allow deletion
                        try:
                            os.chmod(q_path, 0o600)
                        except OSError:
                            pass
                        os.remove(q_path)

                    # Remove metadata sidecar
                    meta_path = q_path + ".meta.json"
                    if os.path.exists(meta_path):
                        os.remove(meta_path)

                except PermissionError:
                    return False, f"Permission denied deleting '{q_path}'."
                except OSError as exc:
                    return False, f"OS error during deletion: {exc}"

                self.data["quarantine"].pop(i)
                self.save_data()
                return True, "File permanently deleted."

        return False, f"Quarantine record '{quarantine_id}' not found."

    def secure_read_file(self, file_path: str, limit: int = None) -> tuple[bool, str, bool]:
        """
        Safely read a file locked with 0o000 permissions.
        Returns (success: bool, content: str, is_binary: bool).
        """
        if not os.path.exists(file_path):
            return False, "File not found.", False

        content = ""
        is_binary = False

        try:
            # Grant read permission (read-only for owner)
            os.chmod(file_path, 0o400)

            with open(file_path, "rb") as f:
                raw_data = f.read(limit) if limit else f.read()
                
                # Simple binary detection (check for null bytes)
                if b'\x00' in raw_data:
                    is_binary = True
                
                content = raw_data.decode("utf-8", errors="ignore")
            
            return True, content, is_binary
        except Exception as exc:
            return False, f"Read error: {exc}", False
        finally:
            # Always reset to 0o000 (standard for quarantined files)
            try:
                os.chmod(file_path, 0o000)
            except OSError:
                pass

