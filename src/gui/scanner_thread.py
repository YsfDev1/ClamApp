"""
ScannerThread — runs clamscan in a background QThread.

Improvements over original:
  - Emits progress(str) with each scanned file path (stdout line-by-line).
  - Robust stop() via SIGTERM to the whole process group.
  - Full try/except with PermissionError differentiation.
"""
import subprocess
import os
import signal
from PyQt6.QtCore import QThread, pyqtSignal


class ScannerThread(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)   # emits current file path being scanned

    def __init__(self, clamscan_path: str, path_to_scan: str):
        super().__init__()
        self.clamscan_path = clamscan_path
        self.path_to_scan = path_to_scan
        self.process = None
        self._stop_requested = False

    # ── Main thread work ───────────────────────────────────────────────────
    def run(self):
        if not self.clamscan_path:
            self.finished.emit({"status": "error", "message": "ClamAV binary not found.", "output": ""})
            return

        try:
            self.process = subprocess.Popen(
                [self.clamscan_path, "-r", "-i", "--stdout", self.path_to_scan],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid,   # Create new process group → killpg works
            )

            stdout_lines = []
            # Read stdout line-by-line to emit live progress
            for line in self.process.stdout:
                line = line.rstrip()
                stdout_lines.append(line)
                # Progress signal: show any non-empty line that isn't "FOUND"
                if line and "FOUND" not in line and not line.startswith("---"):
                    self.progress.emit(line)
                if self._stop_requested:
                    break

            # Wait for process to exit and collect returncode
            stderr_output = self.process.stderr.read() if self.process.stderr else ""
            self.process.wait()
            returncode = self.process.returncode
            full_output = "\n".join(stdout_lines)

            if self._stop_requested:
                self.finished.emit({"status": "stopped", "message": "Scan stopped by user.", "output": full_output})
            elif returncode == 0:
                self.finished.emit({"status": "clean", "message": "No threats found.", "output": full_output})
            elif returncode == 1:
                self.finished.emit({"status": "infected", "message": "Threats detected!", "output": full_output})
            else:
                self.finished.emit({
                    "status": "error",
                    "message": stderr_output.strip() or f"clamscan exited with code {returncode}.",
                    "output": full_output,
                })

        except PermissionError as exc:
            self.finished.emit({"status": "error", "message": f"Permission denied: {exc}", "output": ""})
        except FileNotFoundError:
            self.finished.emit({"status": "error", "message": "clamscan binary not found on PATH.", "output": ""})
        except Exception as exc:
            self.finished.emit({"status": "error", "message": str(exc), "output": ""})

    # ── Stop ───────────────────────────────────────────────────────────────
    def stop(self):
        """Request the scan to stop; signal the clamscan process group."""
        self._stop_requested = True
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
