import subprocess
import os
import signal
from PyQt6.QtCore import QThread, pyqtSignal

class ScannerThread(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, clamscan_path, path_to_scan):
        super().__init__()
        self.clamscan_path = clamscan_path
        self.path_to_scan = path_to_scan
        self.process = None

    def run(self):
        if not self.clamscan_path:
            self.finished.emit({"status": "error", "message": "ClamAV not found"})
            return

        try:
            # -r for recursive, -i for infected only
            # We use subprocess.Popen so we can terminate it
            self.process = subprocess.Popen(
                [self.clamscan_path, "-r", "-i", self.path_to_scan],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid # To kill the group
            )
            
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0:
                self.finished.emit({"status": "clean", "message": "No threats found", "output": stdout})
            elif self.process.returncode == 1:
                self.finished.emit({"status": "infected", "message": "Threats detected!", "output": stdout})
            else:
                self.finished.emit({"status": "error", "message": stderr or "Scan failed", "output": stdout})
                
        except Exception as e:
            self.finished.emit({"status": "error", "message": str(e)})

    def stop(self):
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
