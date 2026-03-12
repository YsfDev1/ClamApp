import os
import shutil

class StartupManagerLogic:
    """
    Lists and manages autostart items (.desktop files).
    """
    USER_PATH = os.path.expanduser("~/.config/autostart/")
    SYSTEM_PATH = "/etc/xdg/autostart/"

    @staticmethod
    def list_items():
        items = []
        for path in [StartupManagerLogic.USER_PATH, StartupManagerLogic.SYSTEM_PATH]:
            if not os.path.exists(path):
                continue
            for filename in os.listdir(path):
                if filename.endswith(".desktop"):
                    full_path = os.path.join(path, filename)
                    info = StartupManagerLogic._parse_desktop_file(full_path)
                    if info:
                        info["path"] = full_path
                        info["is_system"] = (path == StartupManagerLogic.SYSTEM_PATH)
                        items.append(info)
        return items

    @staticmethod
    def _parse_desktop_file(path):
        try:
            name = ""
            cmd = ""
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith("Name="):
                        name = line.split("=")[1].strip()
                    elif line.startswith("Exec="):
                        cmd = line.split("=")[1].strip()
            return {"name": name or os.path.basename(path), "command": cmd}
        except Exception:
            return None

    @staticmethod
    def disable_item(path):
        """
        Disables an item by moving it to a backup or deleting (user path only).
        Or simply adding X-GNOME-Autostart-enabled=false.
        Here we will try to rename to .disabled for user files.
        """
        try:
            if not os.path.exists(path):
                return False, "File does not exist."
            
            # If system file, we might need sudo (usually we can't touch it without root)
            if StartupManagerLogic.SYSTEM_PATH in path:
                return False, "Permission denied (System file)."
            
            os.rename(path, path + ".disabled")
            return True, "Disabled successfully."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def remove_item(path):
        try:
            if StartupManagerLogic.SYSTEM_PATH in path:
                return False, "Permission denied (System file)."
            os.remove(path)
            return True, "Removed successfully."
        except Exception as e:
            return False, str(e)
