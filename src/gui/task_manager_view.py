from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLineEdit, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.task_manager import TaskManagerLogic

class TaskWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        procs = TaskManagerLogic.get_processes()
        self.finished.emit(procs)

class TaskManagerView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.proc_data = {} # pid -> row_index
        self.init_ui()
        
        self.worker = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.request_update)
        self.timer.start(2000)
        self.request_update()

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#1e66f5"
        
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.search_input.setStyleSheet(f"background-color: {card}; color: {text}; border: 1px solid {accent}; border-radius: 8px; padding: 10px;")
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {card}; color: {text}; border: none; border-radius: 8px; }}
            QHeaderView::section {{ background-color: {bg}; color: {accent}; font-weight: bold; border: none; padding: 8px; }}
        """)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        header = QHBoxLayout()
        self.title = QLabel("Task Manager")
        header.addWidget(self.title)
        header.addStretch()
        
        self.info_lbl = QLabel("Auto-refreshing every 2s")
        self.info_lbl.setStyleSheet("color: #bac2de; font-style: italic;")
        header.addWidget(self.info_lbl)
        layout.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter processes...")
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PID", "Name", "User", "CPU %", "Mem %", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def request_update(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = TaskWorker()
        self.worker.finished.connect(self.update_table)
        self.worker.start()

    def update_table(self, processes):
        query = self.search_input.text().lower()
        filtered = [p for p in processes if query in p['name'].lower()]
        
        # Differential update:
        # Instead of clearing, we sync the table with 'filtered'
        current_pids = {p['pid'] for p in filtered}
        
        # 1. Remove rows for PIDs no longer present
        for i in reversed(range(self.table.rowCount())):
            pid_item = self.table.item(i, 0)
            if pid_item:
                pid = int(pid_item.text())
                if pid not in current_pids:
                    self.table.removeRow(i)
        
        # 2. Update existing or add new
        # Mapping PID to existing row index after removals
        pid_to_row = {}
        for i in range(self.table.rowCount()):
            pid_item = self.table.item(i, 0)
            if pid_item:
                pid_to_row[int(pid_item.text())] = i

        for p in filtered:
            pid = p['pid']
            if pid in pid_to_row:
                idx = pid_to_row[pid]
                self.table.item(idx, 3).setText(f"{p['cpu_percent']}%")
                self.table.item(idx, 4).setText(f"{p['memory_percent']:.1f}%")
            else:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(pid)))
                self.table.setItem(row, 1, QTableWidgetItem(p['name']))
                self.table.setItem(row, 2, QTableWidgetItem(p['username']))
                self.table.setItem(row, 3, QTableWidgetItem(f"{p['cpu_percent']}%"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{p['memory_percent']:.1f}%"))
                
                btn = QPushButton("End Task")
                btn.setStyleSheet("background-color: #f38ba8; color: #11111b; font-size: 10px; border-radius: 3px;")
                btn.clicked.connect(lambda _, pid=pid: self.end_task(pid))
                self.table.setCellWidget(row, 5, btn)

    def end_task(self, pid):
        success, msg = TaskManagerLogic.kill_process(pid)
        if not success:
            QMessageBox.warning(self, "Error", msg)
        else:
            self.request_update()

    def retranslate(self):
        self.title.setText(self.trans.get("task_manager"))
        self.info_lbl.setText(self.trans.get("auto_refresh_task"))
        self.table.setHorizontalHeaderLabels([
            self.trans.get("pid"), self.trans.get("process_name"),
            self.trans.get("user"), self.trans.get("cpu"),
            self.trans.get("memory"), self.trans.get("actions")
        ])
