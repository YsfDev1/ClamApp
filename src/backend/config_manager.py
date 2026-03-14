import json
import os

class SettingsManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/clamapp")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self._ensure_config_dir()
        self.config = self.load_config()

    def _ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Default settings
        return {
            "vt_api_key": "",
            "daily_scan_enabled": False,
            "scan_time": "03:00"
        }

    def save_config(self, config_data=None):
        if config_data:
            self.config.update(config_data)
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
