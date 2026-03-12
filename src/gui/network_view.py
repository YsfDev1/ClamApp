<<<<<<< HEAD
"""
NetworkView — displays active network connections using a background thread.

Changes from original:
  - Removed QTimer-based direct psutil calls on the main thread.
  - Uses NetworkMonitorThread which polls every 2 s in a background QThread.
  - _update_table() slot runs on the GUI thread safely via signal/slot.
  - Shows kill-process button per connection.
  - Handles psutil unavailability and AccessDenied errors gracefully.
"""
=======
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
<<<<<<< HEAD

import os
import sys
if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from gui.network_monitor_thread import NetworkMonitorThread


=======
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
class NetworkView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.is_dark = True
<<<<<<< HEAD
        self._monitor_thread = None
        self._init_ui()
        self._start_monitor()

    # ── UI setup ───────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

=======
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_connections)
        self.timer.start(5000)
        self.refresh_connections()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
        header = QHBoxLayout()
        self.title = QLabel(self.trans.get("active_connections"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        header.addWidget(self.title)
<<<<<<< HEAD
        header.addStretch()

        self.btn_refresh = QPushButton(self.trans.get("refresh"))
        self.btn_refresh.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 5px;"
        )
        self.btn_refresh.clicked.connect(self._manual_refresh)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.info_label = QLabel(self.trans.get("auto_refresh_5s"))
        self.info_label.setStyleSheet("color: #585b70; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"), self.trans.get("pid"),
            self.trans.get("process_name"), self.trans.get("local_addr"),
            self.trans.get("remote_addr"), self.trans.get("status"),
            self.trans.get("actions"),
=======
        
        header.addStretch()
        
        self.btn_refresh = QPushButton(self.trans.get("refresh"))
        self.btn_refresh.setStyleSheet("background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_refresh.clicked.connect(self.refresh_connections)
        header.addWidget(self.btn_refresh)
        
        layout.addLayout(header)
        
        self.info_label = QLabel(self.trans.get("auto_refresh_5s"))
        self.info_label.setStyleSheet("color: #585b70; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.info_label)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"), self.trans.get("pid"), 
            self.trans.get("process_name"), self.trans.get("local_addr"), 
            self.trans.get("remote_addr"), self.trans.get("status"),
            self.trans.get("actions")
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #313244; color: #cdd6f4;")
        layout.addWidget(self.table)

<<<<<<< HEAD
    # ── Thread management ──────────────────────────────────────────────────

    def _start_monitor(self):
        """Start the background network monitoring thread."""
        if not HAS_PSUTIL:
            self._show_psutil_missing()
            return

        self._monitor_thread = NetworkMonitorThread(interval=2.0, parent=self)
        self._monitor_thread.data_ready.connect(self._update_table)
        self._monitor_thread.error_occurred.connect(self._on_monitor_error)
        self._monitor_thread.start()

    def _stop_monitor(self):
        if self._monitor_thread and self._monitor_thread.isRunning():
            self._monitor_thread.stop()
            self._monitor_thread = None

    def _manual_refresh(self):
        """Force an immediate poll by restarting the thread."""
        self._stop_monitor()
        QTimer.singleShot(100, self._start_monitor)

    # ── Slot: called on GUI thread via signal (safe for QTableWidget) ──────

    def _update_table(self, connections: list):
        self.table.setRowCount(len(connections))
        c = self._colors()

        for i, conn in enumerate(connections):
            self.table.setItem(i, 0, QTableWidgetItem(conn["proto"]))
            self.table.setItem(i, 1, QTableWidgetItem(conn["pid"]))
            self.table.setItem(i, 2, QTableWidgetItem(conn["name"]))
            self.table.setItem(i, 3, QTableWidgetItem(conn["laddr"]))
            self.table.setItem(i, 4, QTableWidgetItem(conn["raddr"]))

            status_item = QTableWidgetItem(conn["status"])
            status_item.setForeground(self._status_color(conn["status"]))
            self.table.setItem(i, 5, status_item)

            # Kill-process button only when pid is known
            pid_str = conn.get("pid", "—")
            if pid_str and pid_str != "—":
                btn_kill = QPushButton(self.trans.get("kill_process"))
                btn_kill.setStyleSheet(
                    f"background-color: #f38ba8; color: #11111b;"
                    f" font-size: 10px; border-radius: 3px; padding: 2px;"
                )
                btn_kill.clicked.connect(lambda _, p=int(pid_str): self._kill_process(p))
                self.table.setCellWidget(i, 6, btn_kill)

    def _on_monitor_error(self, message: str):
        self.table.setRowCount(1)
        item = QTableWidgetItem(f"⚠ {message}")
        item.setForeground(QColor("#f38ba8"))
        self.table.setItem(0, 2, item)

    def _show_psutil_missing(self):
        self.table.setRowCount(1)
        item = QTableWidgetItem("psutil not installed — run: pip install psutil")
        item.setForeground(QColor("#f38ba8"))
        self.table.setItem(0, 2, item)

    # ── Actions ────────────────────────────────────────────────────────────

    def _kill_process(self, pid: int):
        if not HAS_PSUTIL:
            return
        try:
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            QMessageBox.information(
                self, "Process Killed",
                f"Process '{name}' (PID {pid}) was terminated.",
            )
            # Trigger a quick refresh after kill
            QTimer.singleShot(600, self._manual_refresh)
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Error", f"PID {pid} no longer exists.")
        except psutil.AccessDenied:
            QMessageBox.warning(self, "Permission Denied",
                                f"Cannot terminate PID {pid}. Try running ClamApp as root.")
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))

    # ── Helpers ────────────────────────────────────────────────────────────

    def _colors(self):
        return {
            "card": "#313244" if self.is_dark else "#ccd0da",
            "text": "#cdd6f4" if self.is_dark else "#4c4f69",
            "accent": "#89b4fa" if self.is_dark else "#1e66f5",
        }

    @staticmethod
    def _status_color(status: str) -> QColor:
        mapping = {
            "ESTABLISHED": QColor("#a6e3a1"),
            "LISTEN":      QColor("#89b4fa"),
            "TIME_WAIT":   QColor("#fab387"),
            "CLOSE_WAIT":  QColor("#f38ba8"),
        }
        return mapping.get(status, QColor("#cdd6f4"))

    # ── Theming / translation ──────────────────────────────────────────────

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = self._colors()
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {c['accent']};")
        self.table.setStyleSheet(
            f"background-color: {c['card']}; color: {c['text']}; gridline-color: {c['accent']};"
        )
        self.btn_refresh.setStyleSheet(
            f"background-color: {c['card']}; color: {c['text']}; font-weight: bold; padding: 10px; border-radius: 5px;"
        )
=======
    def refresh_connections(self):
        if not HAS_PSUTIL:
            self.table.setRowCount(1)
            item = QTableWidgetItem("psutil library is not installed. Please install it using 'pip install psutil'.")
            item.setForeground(QColor("#f38ba8"))
            self.table.setItem(0, 2, item)
            return

        try:
            connections = psutil.net_connections(kind='inet')
            self.table.setRowCount(len(connections))
            
            for i, conn in enumerate(connections):
                # Proto
                proto = "TCP" if conn.type == 1 else "UDP"
                self.table.setItem(i, 0, QTableWidgetItem(proto))
                
                # PID
                pid = str(conn.pid) if conn.pid else "-"
                self.table.setItem(i, 1, QTableWidgetItem(pid))
                
                # Process Name
                name = "Unknown"
                if conn.pid:
                    try:
                        name = psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self.table.setItem(i, 2, QTableWidgetItem(name))
                
                # Local Addr
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
                self.table.setItem(i, 3, QTableWidgetItem(laddr))
                
                # Remote Addr
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
                self.table.setItem(i, 4, QTableWidgetItem(raddr))
                
                # Status
                status = conn.status
                item = QTableWidgetItem(status)
                
                # Color code status
                if status == "ESTABLISHED":
                    item.setForeground(QColor("#a6e3a1")) # Green
                elif status == "LISTEN":
                    item.setForeground(QColor("#89b4fa")) # Blue
                elif status == "TIME_WAIT":
                    item.setForeground(QColor("#fab387")) # Orange
                
                self.table.setItem(i, 5, item)

                # Actions
                if conn.pid:
                    btn_kill = QPushButton(self.trans.get("kill_process"))
                    btn_kill.setStyleSheet("background-color: #f38ba8; color: #11111b; font-size: 10px; border-radius: 3px;")
                    btn_kill.clicked.connect(lambda _, p=conn.pid: self.kill_connection_process(p))
                    self.table.setCellWidget(i, 6, btn_kill)
                
        except Exception as e:
            # Silently fail if psutil has issues, or log it
            pass

    def kill_connection_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            QTimer.singleShot(500, self.refresh_connections)
        except Exception:
            pass

    def apply_theme(self, dark=True):
        self.is_dark = dark
        if dark:
            card, text, accent = "#313244", "#cdd6f4", "#89b4fa"
        else:
            card, text, accent = "#ccd0da", "#4c4f69", "#1e66f5"
            
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.table.setStyleSheet(f"background-color: {card}; color: {text}; gridline-color: {accent};")
        self.btn_refresh.setStyleSheet(f"background-color: {card}; color: {text}; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.info_label.setStyleSheet("color: #585b70; font-style: italic; margin-bottom: 10px;")
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b

    def retranslate(self):
        self.title.setText(self.trans.get("active_connections"))
        self.btn_refresh.setText(self.trans.get("refresh"))
        self.info_label.setText(self.trans.get("auto_refresh_5s"))
        self.table.setHorizontalHeaderLabels([
<<<<<<< HEAD
            self.trans.get("proto"), self.trans.get("pid"),
            self.trans.get("process_name"), self.trans.get("local_addr"),
            self.trans.get("remote_addr"), self.trans.get("status"),
            self.trans.get("actions"),
        ])

    # ── Cleanup ────────────────────────────────────────────────────────────

    def hideEvent(self, event):
        """Pause monitoring when the tab is hidden to save CPU."""
        self._stop_monitor()
        super().hideEvent(event)

    def showEvent(self, event):
        """Resume monitoring when the tab becomes visible."""
        if self._monitor_thread is None or not self._monitor_thread.isRunning():
            self._start_monitor()
        super().showEvent(event)

    def closeEvent(self, event):
        self._stop_monitor()
        super().closeEvent(event)
=======
            self.trans.get("proto"), self.trans.get("pid"), 
            self.trans.get("process_name"), self.trans.get("local_addr"), 
            self.trans.get("remote_addr"), self.trans.get("status")
        ])
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
