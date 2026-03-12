from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QProgressBar, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.data_shredder import DataShredder

class ShredderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        # We can't easily track progress of low-level write, 
        # but we can simulate passes for the UI.
        success, message = DataShredder.shred_file(self.file_path, passes=3)
        self.finished.emit(success, message)

class ShredderView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel(self.trans.get("data_destroyer"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f38ba8;")
        layout.addWidget(self.title)

        self.desc = QLabel(self.trans.get("shred_desc") if self.trans.get("shred_desc") != "shred_desc" else "Securely delete files by overwriting them with random data. Once shredded, files cannot be recovered.")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        layout.addWidget(self.desc)

        # File selection card
        self.card = QFrame()
        self.card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px;")
        card_layout = QVBoxLayout(self.card)

        self.btn_select = QPushButton(self.trans.get("select_shred"))
        self.btn_select.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 15px; border-radius: 5px;")
        self.btn_select.clicked.connect(self.select_file)
        card_layout.addWidget(self.btn_select)

        self.file_label = QLabel(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
        self.file_label.setStyleSheet("color: #bac2de; margin-top: 10px;")
        card_layout.addWidget(self.file_label)

        layout.addWidget(self.card)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #45475a; border-radius: 5px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #f38ba8; }
        """)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setHidden(True)
        layout.addWidget(self.progress_bar)

        self.btn_shred = QPushButton(self.trans.get("permanently_shred"))
        self.btn_shred.setEnabled(False)
        self.btn_shred.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 15px; border-radius: 5px;")
        self.btn_shred.clicked.connect(self.start_shredding)
        layout.addWidget(self.btn_shred)

        layout.addStretch()

        self.selected_file = None
        self.thread = None

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#f38ba8"
        else:
            bg, card, text, accent = "#eff1f5", "#ccd0da", "#4c4f69", "#d20f39"
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.desc.setStyleSheet(f"color: {text}; font-size: 14px;")
        self.card.setStyleSheet(f"background-color: {card}; border-radius: 10px; padding: 20px;")
        self.file_label.setStyleSheet(f"color: {text}; margin-top: 10px;")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.trans.get("select_shred"))
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"{self.trans.get('target') if self.trans.get('target') != 'target' else 'Target'}: {os.path.basename(file_path)}")
            self.btn_shred.setEnabled(True)

    def start_shredding(self):
        if not self.selected_file:
            return

        reply = QMessageBox.warning(self, self.trans.get("shred_confirm"), 
                                   self.trans.get("shred_warn"),
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.btn_shred.setEnabled(False)
            self.btn_select.setEnabled(False)
            self.progress_bar.setHidden(False)
            
            self.thread = ShredderThread(self.selected_file)
            self.thread.finished.connect(self.on_finished)
            self.thread.start()

    def on_finished(self, success, message):
        self.progress_bar.setHidden(True)
        self.btn_select.setEnabled(True)
        self.btn_shred.setEnabled(False)
        self.file_label.setText(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
        self.selected_file = None

        if success:
            QMessageBox.information(self, self.trans.get("success") if self.trans.get("success") != "success" else "Success", message)
        else:
            QMessageBox.critical(self, self.trans.get("error") if self.trans.get("error") != "error" else "Error", message)

    def retranslate(self):
        self.title.setText(self.trans.get("data_destroyer"))
        self.desc.setText(self.trans.get("shred_desc") if self.trans.get("shred_desc") != "shred_desc" else "Securely delete files by overwriting them with random data. Once shredded, files cannot be recovered.")
        self.btn_select.setText(self.trans.get("select_shred"))
        self.btn_shred.setText(self.trans.get("permanently_shred"))
        if not self.selected_file:
            self.file_label.setText(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
        else:
            self.file_label.setText(f"{self.trans.get('target') if self.trans.get('target') != 'target' else 'Target'}: {os.path.basename(self.selected_file)}")

