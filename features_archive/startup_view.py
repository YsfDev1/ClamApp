from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.startup_manager import StartupManagerLogic

class StartupView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()
        self.load_items()

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#1e66f5"
        
        self.setAutoFillBackground(True)
        p = self.palette()
        from PyQt6.QtGui import QColor
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {card}; color: {text}; border: none; border-radius: 8px; }}
            QHeaderView::section {{ background-color: {bg}; color: {accent}; font-weight: bold; border: none; padding: 8px; }}
        """)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        self.title = QLabel("Startup Manager")
        layout.addWidget(self.title)

        self.lbl_info = QLabel("Review applications that start automatically with your system.")
        self.lbl_info.setStyleSheet("color: #bac2de; font-style: italic;")
        layout.addWidget(self.lbl_info)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Command", "Location"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_items)
        self.btn_refresh.setStyleSheet("background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 6px;")
        
        self.btn_disable = QPushButton("Disable Selected")
        self.btn_disable.clicked.connect(self.disable_selected)
        self.btn_disable.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_disable)
        layout.addLayout(btn_row)

    def load_items(self):
        self.items = StartupManagerLogic.list_items()
        self.table.setRowCount(0)
        for item in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["command"]))
            loc = "System" if item["is_system"] else "User"
            self.table.setItem(row, 2, QTableWidgetItem(loc))

    def disable_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        item = self.items[row]
        if item["is_system"]:
            QMessageBox.warning(self, "Access Denied", "System autostart items require root privileges to modify.")
            return

        reply = QMessageBox.question(self, "Confirm", f"Are you sure you want to disable '{item['name']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = StartupManagerLogic.disable_item(item["path"])
            if success:
                QMessageBox.information(self, "Success", msg)
                self.load_items()
            else:
                QMessageBox.critical(self, "Error", msg)

    def retranslate(self):
        self.title.setText(self.trans.get("startup_manager"))
        self.btn_refresh.setText(self.trans.get("refresh"))
        self.btn_disable.setText(self.trans.get("disable_item"))
        # More updates here
