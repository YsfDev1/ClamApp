import json
import os
import shutil
from datetime import datetime

class DataManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.data_file = os.path.join(base_dir, "app_data.json")
        self.quarantine_dir = os.path.join(base_dir, "quarantine")
        
        if not os.path.exists(self.quarantine_dir):
            os.makedirs(self.quarantine_dir)
            
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    # Ensure new keys exist
                    if "scan_history" not in data:
                        data["scan_history"] = []
                    if "settings" not in data:
                        data["settings"] = {"language": "en"}
                    if "quarantine" in data:
                        for i, item in enumerate(data["quarantine"]):
                            if "id" not in item:
                                # Use timestamp or index if missing
                                item["id"] = f"migrated_{i}"
                        self.data = data
                        self.save_data()
                    return data
            except:
                pass
        return {
            "stats": {"total_scans": 0, "threats_found": 0, "objects_scanned": 0},
            "quarantine": [],
            "scan_history": [],
            "settings": {"language": "en"}
        }

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_scan_result(self, threats, objects=100, scan_type="Custom", path=""):
        self.data["stats"]["total_scans"] += 1
        self.data["stats"]["threats_found"] += threats
        self.data["stats"]["objects_scanned"] += objects
        
        self.data["scan_history"].insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": scan_type,
            "path": path,
            "threats": threats,
            "objects": objects
        })
        # Keep only last 50 scans
        self.data["scan_history"] = self.data["scan_history"][:50]
        self.save_data()

    def quarantine_file(self, file_path):
        if not os.path.exists(file_path):
            return False
        
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{filename}"
        dest_path = os.path.join(self.quarantine_dir, safe_name)
        
        try:
            shutil.move(file_path, dest_path)
            self.data["quarantine"].append({
                "id": timestamp,
                "original_path": file_path,
                "quarantine_path": dest_path,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            self.save_data()
            return True
        except Exception as e:
            print(f"Quarantine failed: {e}")
            return False

    def restore_file(self, quarantine_id):
        for i, item in enumerate(self.data["quarantine"]):
            if item["id"] == quarantine_id:
                try:
                    shutil.move(item["quarantine_path"], item["original_path"])
                    self.data["quarantine"].pop(i)
                    self.save_data()
                    return True
                except:
                    return False
        return False

    def delete_permanently(self, quarantine_id):
        for i, item in enumerate(self.data["quarantine"]):
            if item["id"] == quarantine_id:
                try:
                    if os.path.exists(item["quarantine_path"]):
                        os.remove(item["quarantine_path"])
                    self.data["quarantine"].pop(i)
                    self.save_data()
                    return True
                except:
                    return False
        return False
