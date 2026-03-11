try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

class NetworkView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.is_dark = True
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_connections)
        self.timer.start(5000)
        self.refresh_connections()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        self.title = QLabel(self.trans.get("active_connections"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        header.addWidget(self.title)
        
        header.addStretch()
        
        self.btn_refresh = QPushButton(self.trans.get("refresh"))
        self.btn_refresh.setStyleSheet("background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_refresh.clicked.connect(self.refresh_connections)
        header.addWidget(self.btn_refresh)
        
        layout.addLayout(header)
        
        self.info_label = QLabel(self.trans.get("auto_refresh_5s"))
        self.info_label.setStyleSheet("color: #585b70; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.info_label)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"), self.trans.get("pid"), 
            self.trans.get("process_name"), self.trans.get("local_addr"), 
            self.trans.get("remote_addr"), self.trans.get("status")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #313244; color: #cdd6f4;")
        layout.addWidget(self.table)

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
                
        except Exception as e:
            # Silently fail if psutil has issues, or log it
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

    def retranslate(self):
        self.title.setText(self.trans.get("active_connections"))
        self.btn_refresh.setText(self.trans.get("refresh"))
        self.info_label.setText(self.trans.get("auto_refresh_5s"))
        self.table.setHorizontalHeaderLabels([
            self.trans.get("proto"), self.trans.get("pid"), 
            self.trans.get("process_name"), self.trans.get("local_addr"), 
            self.trans.get("remote_addr"), self.trans.get("status")
        ])
