"""
NetworkMonitorThread — runs psutil network polling in a background QThread.
Emits data_ready(list[dict]) every ~2 seconds so the UI never freezes.
"""
import time
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from PyQt6.QtCore import QThread, pyqtSignal


class NetworkMonitorThread(QThread):
    """
    Background thread that polls network connections and emits results.
    Uses time.sleep(2.0) to avoid 100% CPU usage.
    """
    data_ready = pyqtSignal(list)   # list[dict]
    error_occurred = pyqtSignal(str)

    def __init__(self, interval: float = 2.0, parent=None):
        super().__init__(parent)
        self._running = False
        self.interval = interval

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def run(self):
        self._running = True
        if not HAS_PSUTIL:
            self.error_occurred.emit("psutil not installed. Run: pip install psutil")
            return

        while self._running:
            try:
                connections = self._collect()
                if self._running:          # check again before emitting
                    self.data_ready.emit(connections)
            except Exception as exc:
                if self._running:
                    self.error_occurred.emit(str(exc))
            # Sleep in small chunks so stop() reacts quickly
            for _ in range(int(self.interval / 0.2)):
                if not self._running:
                    break
                time.sleep(0.2)

    def stop(self):
        """Signal the loop to exit and wait for thread to finish."""
        self._running = False
        self.wait(3000)  # Wait up to 3 s

    # ── Data collection (runs in worker thread) ────────────────────────────
    def _collect(self) -> list:
        results = []
        try:
            connections = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            # On some Linux systems listing all conns requires root; degrade gracefully
            connections = psutil.net_connections(kind="inet4")

        for conn in connections:
            try:
                pid = conn.pid
                name = "—"
                if pid:
                    try:
                        name = psutil.Process(pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                        pass

                proto = "TCP" if conn.type == 1 else "UDP"
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "—"
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "—"
                status = getattr(conn, "status", "—") or "—"

                results.append({
                    "proto": proto,
                    "pid": str(pid) if pid else "—",
                    "name": name,
                    "laddr": laddr,
                    "raddr": raddr,
                    "status": status,
                })
            except Exception:
                # Skip any single malformed entry and continue
                continue

        return results
