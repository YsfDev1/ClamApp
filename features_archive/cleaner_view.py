from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QFrame, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.system_cleaner import SystemCleanerLogic

class CleanerWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int) # count, size

    def run(self):
        count, size = SystemCleanerLogic.clean(on_progress=self.progress.emit)
        self.finished.emit(count, size)

class CleanerView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

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
        self.summary_card.setStyleSheet(f"background-color: {card}; border-radius: 12px; padding: 20px;")
        self.lbl_status.setStyleSheet(f"color: {text}; font-size: 16px;")
        self.progress_bar.setStyleSheet(f"QProgressBar {{ background-color: {bg}; border: 1px solid {accent}; border-radius: 5px; text-align: center; color: {text}; }} QProgressBar::chunk {{ background-color: {accent}; }}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.title = QLabel("System Hygiene") # Translation will be added later
        layout.addWidget(self.title)

        self.summary_card = QFrame()
        card_layout = QVBoxLayout(self.summary_card)
        
        self.lbl_status = QLabel("Ready to scan your system for clutter.")
        self.lbl_status.setWordWrap(True)
        card_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        card_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton("Scan (Dry Run)")
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_scan.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        
        self.btn_clean = QPushButton("Clean System")
        self.btn_clean.clicked.connect(self.start_clean)
        self.btn_clean.setEnabled(False)
        self.btn_clean.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        
        btn_row.addWidget(self.btn_scan)
        btn_row.addWidget(self.btn_clean)
        card_layout.addLayout(btn_row)

        layout.addWidget(self.summary_card)
        layout.addStretch()

    def start_scan(self):
        summary, total_size = SystemCleanerLogic.scan()
        mb = total_size / (1024 * 1024)
        status_text = f"Scan Complete.\n\nTotal size found: {mb:.2f} MB\n\n"
        for name, info in summary.items():
            status_text += f"• {name}: {info['count']} items ({info['size']/(1024*1024):.2f} MB)\n"
        
        self.lbl_status.setText(status_text)
        self.btn_clean.setEnabled(total_size > 0)

    def start_clean(self):
        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = CleanerWorker()
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_clean_finished)
        self.worker.start()

    def on_clean_finished(self, count, size):
        mb = size / (1024 * 1024)
        self.lbl_status.setText(f"System Cleaned!\n\nSuccessfully removed {count} items.\nFreed space: {mb:.2f} MB")
        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_clean.setEnabled(False)

    def retranslate(self):
        # We will update these once translations are added
        self.title.setText(self.trans.get("system_hygiene"))
        self.btn_scan.setText(self.trans.get("cleaner_scan"))
        self.btn_clean.setText(self.trans.get("cleaner_clean"))
        if "Ready" in self.lbl_status.text():
            self.lbl_status.setText(self.trans.get("cleaner_ready"))
