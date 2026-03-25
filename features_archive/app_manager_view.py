from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLineEdit, QFrame, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.app_manager import AppManagerLogic

class AppListWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        apps = AppManagerLogic.list_apps()
        self.finished.emit(apps)

class AppManagerView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.all_apps = []
        self.init_ui()
        self.refresh_list()

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
        self.search_input.setStyleSheet(f"background-color: {card}; color: {text}; border: 1px solid {accent}; border-radius: 8px; padding: 10px;")
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {card}; color: {text}; border: none; border-radius: 8px; }}
            QHeaderView::section {{ background-color: {bg}; color: {accent}; font-weight: bold; border: none; padding: 8px; }}
        """)
        self.details_area.setStyleSheet(f"background-color: {card}; color: {text}; border-radius: 8px; padding: 10px; font-family: monospace;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        self.title = QLabel("App Manager")
        layout.addWidget(self.title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search installed packages...")
        self.search_input.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_input)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Version", "Architecture"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_details)
        splitter.addWidget(self.table)

        self.details_area = QTextEdit()
        self.details_area.setReadOnly(True)
        self.details_area.setPlaceholderText("Select a package to see properties.")
        splitter.addWidget(self.details_area)

        layout.addWidget(splitter)

        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.refresh_list)
        self.btn_refresh.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        layout.addWidget(self.btn_refresh)

    def refresh_list(self):
        self.btn_refresh.setEnabled(False)
        self.title.setText("App Manager (Loading...)")
        self.worker = AppListWorker()
        self.worker.finished.connect(self.on_list_finished)
        self.worker.start()

    def on_list_finished(self, apps):
        self.all_apps = apps
        self.filter_list()
        self.btn_refresh.setEnabled(True)
        self.title.setText("App Manager")

    def filter_list(self):
        query = self.search_input.text().lower()
        filtered = [a for a in self.all_apps if query in a["name"].lower() or query in a["summary"].lower()]
        
        self.table.setRowCount(0)
        for app in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(app["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(app["version"]))
            self.table.setItem(row, 2, QTableWidgetItem(app["arch"]))
            self.table.item(row,0).setToolTip(app["summary"])

    def show_details(self):
        row = self.table.currentRow()
        if row < 0: return
        pkg_name = self.table.item(row, 0).text()
        details = AppManagerLogic.get_details(pkg_name)
        self.details_area.setText(details)

    def retranslate(self):
        self.title.setText(self.trans.get("app_manager"))
        self.search_input.setPlaceholderText(self.trans.get("search_apps_hint"))
        self.btn_refresh.setText(self.trans.get("refresh"))
