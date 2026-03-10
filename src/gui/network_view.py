import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


def get_connections():
    """Return list of dicts describing active network connections using ss/proc."""
    rows = []
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            try:
                pname = psutil.Process(conn.pid).name() if conn.pid else "—"
            except Exception:
                pname = "—"
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "—"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "—"
            pid = str(conn.pid) if conn.pid else "—"
            proto = "TCP" if conn.type and conn.type.name == "SOCK_STREAM" else "UDP"
            rows.append({
                "proto": proto,
                "pid": pid,
                "name": pname,
                "local": laddr,
                "remote": raddr,
                "status": conn.status or "—"
            })
    except ImportError:
        # Fallback: parse /proc/net/tcp
        rows.append({"proto": "?", "pid": "?", "name": "psutil not installed", "local": "?", "remote": "?", "status": "Install psutil for details"})
    except Exception as e:
        rows.append({"proto": "?", "pid": "?", "name": str(e), "local": "?", "remote": "?", "status": "Error"})
    return rows


STATUS_COLORS = {
    "ESTABLISHED": "#a6e3a1",
    "LISTEN": "#89b4fa",
    "TIME_WAIT": "#fab387",
    "CLOSE_WAIT": "#f38ba8",
    "SYN_SENT": "#f9e2af",
    "SYN_RECV": "#f9e2af",
}


class NetworkView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.is_dark = True
        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        self.refresh()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        if dark:
            bg, card, text, border, accent = "#181825", "#313244", "#cdd6f4", "#45475a", "#89b4fa"
        else:
            bg, card, text, border, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#c0c0cc", "#1e66f5"
        self.setAutoFillBackground(True)
        p = self.palette()
        from PyQt6.QtGui import QColor
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.count_label.setStyleSheet(f"color: {text};")
        self.auto_label.setStyleSheet(f"color: {'#a6e3a1' if dark else '#40a02b'}; font-size: 11px;")
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {card}; color: {text}; gridline-color: {border}; }}
            QHeaderView::section {{ background-color: {'#45475a' if dark else '#c0c0cc'}; color: {text}; padding: 6px; }}
        """)
        self.btn_refresh.setStyleSheet(f"background-color: {accent}; color: #11111b; font-weight: bold; padding: 8px 18px; border-radius: 5px;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.title = QLabel(self.trans.get("active_connections"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        header.addWidget(self.title)
        header.addStretch()

        self.auto_label = QLabel(self.trans.get("auto_refresh_5s"))
        self.auto_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        header.addWidget(self.auto_label)

        self.btn_refresh = QPushButton(self.trans.get("refresh"))
        self.btn_refresh.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px 18px; border-radius: 5px;")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.count_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"),
            self.trans.get("pid"),
            self.trans.get("process_name"),
            self.trans.get("local_addr"),
            self.trans.get("remote_addr"),
            self.trans.get("status"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #313244; color: #cdd6f4; gridline-color: #45475a; }
            QHeaderView::section { background-color: #45475a; color: #cdd6f4; padding: 6px; }
        """)
        layout.addWidget(self.table)

    def refresh(self):
        conns = get_connections()
        self.table.setRowCount(len(conns))
        for i, c in enumerate(conns):
            self.table.setItem(i, 0, QTableWidgetItem(c["proto"]))
            self.table.setItem(i, 1, QTableWidgetItem(c["pid"]))
            self.table.setItem(i, 2, QTableWidgetItem(c["name"]))
            self.table.setItem(i, 3, QTableWidgetItem(c["local"]))
            self.table.setItem(i, 4, QTableWidgetItem(c["remote"]))

            status_item = QTableWidgetItem(c["status"])
            color = STATUS_COLORS.get(c["status"], "#cdd6f4")
            status_item.setForeground(QColor(color))
            self.table.setItem(i, 5, status_item)

        self.count_label.setText(f"{self.trans.get('connection_count')}: {len(conns)}")

    def retranslate(self):
        self.title.setText(self.trans.get("active_connections"))
        self.btn_refresh.setText(self.trans.get("refresh"))
        self.auto_label.setText(self.trans.get("auto_refresh_5s"))
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"),
            self.trans.get("pid"),
            self.trans.get("process_name"),
            self.trans.get("local_addr"),
            self.trans.get("remote_addr"),
            self.trans.get("status"),
        ])
        self.refresh()
