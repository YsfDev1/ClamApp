import os
import shutil
import glob

class SystemCleanerLogic:
    """
    Scans and cleans system clutter like caches and temp files.
    """
    @staticmethod
    def get_targets():
        home = os.path.expanduser("~")
        return {
            "Browser Cache (Firefox)": glob.glob(os.path.join(home, ".mozilla/firefox/*.default-release/cache2/*")),
            "Browser Cache (Chrome)": glob.glob(os.path.join(home, ".cache/google-chrome/Default/Cache/*")),
            "System Temp": glob.glob("/tmp/*"),
            "User Logs": glob.glob(os.path.join(home, "**/*.log"), recursive=True),
        }

    @staticmethod
    def scan():
        """
        Returns a summary of files and total size for a 'Dry Run'.
        """
        targets = SystemCleanerLogic.get_targets()
        summary = {}
        total_size = 0
        
        for name, paths in targets.items():
            count = 0
            size = 0
            for path in paths:
                try:
                    if os.path.isfile(path) or os.path.islink(path):
                        size += os.path.getsize(path)
                        count += 1
                    elif os.path.isdir(path):
                        # Simple recursive size check if needed, but usually cache2 is flat or shallow
                        pass
                except (PermissionError, FileNotFoundError):
                    continue
            summary[name] = {"count": count, "size": size}
            total_size += size
            
        return summary, total_size

    @staticmethod
    def clean(on_progress=None):
        """
        Deletes identified clutter items.
        """
        targets = SystemCleanerLogic.get_targets()
        all_paths = [p for sublist in targets.values() for p in sublist]
        total = len(all_paths)
        deleted_count = 0
        freed_size = 0

        for i, path in enumerate(all_paths):
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    sz = os.path.getsize(path)
                    os.remove(path)
                    freed_size += sz
                    deleted_count += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    deleted_count += 1
            except Exception:
                # Log error or skip if no permission
                continue
            
            if on_progress:
                on_progress(int((i + 1) / total * 100))
                
        return deleted_count, freed_size
