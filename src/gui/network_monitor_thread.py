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
        self._last_io = {} # pid -> (sent, recv, timestamp)
        self._last_global_io = (0, 0, 0) # (sent, recv, timestamp)

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def run(self):
        self._running = True
        if not HAS_PSUTIL:
            self.error_occurred.emit("psutil not installed. Run: pip install psutil")
            return

        while self._running:
            try:
                connections = self._collect()
                if self._running:
                    self.data_ready.emit(connections)
            except Exception as exc:
                if self._running:
                    log.error("Network monitor error: %s", exc)
                    self.error_occurred.emit(str(exc))
            
            for _ in range(int(self.interval / 0.2)):
                if not self._running:
                    break
                time.sleep(0.2)

    def stop(self):
        self._running = False
        self.wait(3000)

    # ── Data collection (runs in worker thread) ────────────────────────────
    def _collect(self) -> list:
        results = []
        now = time.time()
        
        # Global bandwidth calculation
        try:
            net_io = psutil.net_io_counters()
            curr_global = (net_io.bytes_sent, net_io.bytes_recv, now)
            prev_sent, prev_recv, prev_time = self._last_global_io
            
            if prev_time > 0:
                dt = now - prev_time
                global_up = (curr_global[0] - prev_sent) / dt if dt > 0 else 0
                global_down = (curr_global[1] - prev_recv) / dt if dt > 0 else 0
            else:
                global_up, global_down = 0, 0
            
            self._last_global_io = curr_global
        except Exception:
            global_up, global_down = 0, 0

        try:
            connections = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            connections = psutil.net_connections(kind="inet4")

        # Track seen processes to avoid redundant IO counter checks
        seen_pids = {}

        for conn in connections:
            try:
                pid = conn.pid
                name = "—"
                speed_str = "—"
                
                if pid:
                    if pid in seen_pids:
                        name, speed_str = seen_pids[pid]
                    else:
                        try:
                            proc = psutil.Process(pid)
                            name = proc.name()
                            
                            # Per-process bandwidth
                            try:
                                io = proc.io_counters()
                                curr_io = (io.write_bytes, io.read_bytes, now) # simplified: write=out, read=in
                                if pid in self._last_io:
                                    p_sent, p_recv, p_time = self._last_io[pid]
                                    dt = now - p_time
                                    up = (curr_io[0] - p_sent) / dt if dt > 0 else 0
                                    down = (curr_io[1] - p_recv) / dt if dt > 0 else 0
                                    
                                    if up > 1024*1024 or down > 1024*1024:
                                        speed_str = f"↑{up/1024/1024:.1f} ↓{down/1024/1024:.1f} MB/s"
                                    else:
                                        speed_str = f"↑{up/1024:.1f} ↓{down/1024:.1f} KB/s"
                                else:
                                    speed_str = "0.0 KB/s"
                                self._last_io[pid] = curr_io
                            except (psutil.AccessDenied, AttributeError):
                                speed_str = "—"
                                
                        except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                            name = "—"
                            speed_str = "—"
                        seen_pids[pid] = (name, speed_str)

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
                    "bandwidth": speed_str,
                    "global_up": global_up,
                    "global_down": global_down
                })
            except Exception:
                continue

        # Cleanup old PIDs from self._last_io
        current_pids = set(p for p in seen_pids.keys() if p)
        for p in list(self._last_io.keys()):
            if p not in current_pids:
                del self._last_io[p]

        return results
