from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QProgressBar, QMessageBox, 
                             QFrame, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.privacy_shield import PrivacyShield

class PrivacyThread(QThread):
    finished = pyqtSignal(bool, str)
    metadata_ready = pyqtSignal(dict)

    def __init__(self, action, file_path):
        super().__init__()
        self.action = action # 'metadata' or 'sanitize'
        self.file_path = file_path

    def run(self):
        if self.action == 'metadata':
            data = PrivacyShield.get_metadata(self.file_path)
            self.metadata_ready.emit(data)
        else:
            success, message = PrivacyShield.sanitize_image(self.file_path)
            self.finished.emit(success, message)

class PrivacyView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel("Privacy Shield (Metadata Stripper)")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #a6e3a1;")
        layout.addWidget(self.title)

        self.desc = QLabel("Inspect hidden metadata in images and sanitize them to remove personal information like GPS coordinates and device info.")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        layout.addWidget(self.desc)

        # File selection
        self.card = QFrame()
        self.card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px;")
        card_layout = QVBoxLayout(self.card)

        self.btn_select = QPushButton("Select Image to Inspect")
        self.btn_select.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 15px; border-radius: 5px;")
        self.btn_select.clicked.connect(self.select_image)
        card_layout.addWidget(self.btn_select)

        self.file_label = QLabel("No image selected")
        self.file_label.setStyleSheet("color: #bac2de; margin-top: 10px;")
        card_layout.addWidget(self.file_label)

        layout.addWidget(self.card)

        # Metadata display
        layout.addWidget(QLabel("Extracted Metadata:"))
        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)
        self.metadata_display.setPlaceholderText("Metadata will appear here after inspection...")
        self.metadata_display.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; border-radius: 5px; border: 1px solid #45475a; font-family: monospace;")
        layout.addWidget(self.metadata_display)

        # Sanitize button
        self.btn_sanitize = QPushButton("SANITIZE (Remove Metadata)")
        self.btn_sanitize.setEnabled(False)
        self.btn_sanitize.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 15px; border-radius: 5px;")
        self.btn_sanitize.clicked.connect(self.start_sanitization)
        layout.addWidget(self.btn_sanitize)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #45475a; border-radius: 5px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #a6e3a1; }
        """)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setHidden(True)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        self.selected_file = None
        self.thread = None

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#a6e3a1"
        else:
            bg, card, text, accent = "#eff1f5", "#ccd0da", "#4c4f69", "#40a02b"
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.desc.setStyleSheet(f"color: {text}; font-size: 14px;")
        self.card.setStyleSheet(f"background-color: {card}; border-radius: 10px; padding: 20px;")
        self.file_label.setStyleSheet(f"color: {text}; margin-top: 10px;")
        self.metadata_display.setStyleSheet(f"background-color: {bg}; color: {text}; border-radius: 5px; border: 1px solid {card}; font-family: monospace;")

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", filter="Images (*.jpg *.jpeg *.png)")
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"Target: {os.path.basename(file_path)}")
            self.metadata_display.clear()
            self.btn_sanitize.setEnabled(False)
            
            # Start inspection
            self.btn_select.setEnabled(False)
            self.progress_bar.setHidden(False)
            self.thread = PrivacyThread('metadata', self.selected_file)
            self.thread.metadata_ready.connect(self.on_metadata_ready)
            self.thread.start()

    def on_metadata_ready(self, metadata):
        self.progress_bar.setHidden(True)
        self.btn_select.setEnabled(True)
        
        if not metadata:
            self.metadata_display.setPlainText("No metadata found.")
        elif "Error" in metadata:
            self.metadata_display.setPlainText(metadata["Error"])
        else:
            text = ""
            for k, v in metadata.items():
                text += f"{k}: {v}\n"
            self.metadata_display.setPlainText(text)
            self.btn_sanitize.setEnabled(True)

    def start_sanitization(self):
        if not self.selected_file:
            return

        self.btn_sanitize.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.progress_bar.setHidden(False)
        
        self.thread = PrivacyThread('sanitize', self.selected_file)
        self.thread.finished.connect(self.on_sanitized)
        self.thread.start()

    def on_sanitized(self, success, message):
        self.progress_bar.setHidden(True)
        self.btn_select.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.metadata_display.setPlainText("Image sanitized. Re-select the file to inspect the sanitized version.")
            self.btn_sanitize.setEnabled(False)
        else:
            QMessageBox.critical(self, "Error", message)

    def retranslate(self):
        pass
