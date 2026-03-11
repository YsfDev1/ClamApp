from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QProgressBar, QMessageBox, 
                             QFrame, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.crypto_vault import CryptoVault

class VaultThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, action, file_path, password):
        super().__init__()
        self.action = action # 'encrypt' or 'decrypt'
        self.file_path = file_path
        self.password = password

    def run(self):
        if self.action == 'encrypt':
            success, message = CryptoVault.encrypt_file(self.file_path, self.password)
        else:
            success, message = CryptoVault.decrypt_file(self.file_path, self.password)
        self.finished.emit(success, message)

class VaultView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel("Cryptographic Vault")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        self.desc = QLabel("Securely encrypt or decrypt any file. Use a strong password to protect your data.")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        layout.addWidget(self.desc)

        # Main card
        self.card = QFrame()
        self.card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px;")
        card_layout = QVBoxLayout(self.card)

        # File selection
        file_row = QHBoxLayout()
        self.btn_select = QPushButton("Select File")
        self.btn_select.setStyleSheet("background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_select.clicked.connect(self.select_file)
        file_row.addWidget(self.btn_select)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #bac2de;")
        file_row.addWidget(self.file_label, 1)
        card_layout.addLayout(file_row)

        # Password input
        card_layout.addWidget(QLabel("Security Key (Password):"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter encryption/decryption key...")
        self.password_input.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 10px; border-radius: 5px; border: 1px solid #45475a;")
        card_layout.addWidget(self.password_input)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_encrypt = QPushButton("ENCRYPT")
        self.btn_encrypt.setEnabled(False)
        self.btn_encrypt.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_encrypt.clicked.connect(lambda: self.start_process('encrypt'))
        btn_row.addWidget(self.btn_encrypt)

        self.btn_decrypt = QPushButton("DECRYPT")
        self.btn_decrypt.setEnabled(False)
        self.btn_decrypt.setStyleSheet("background-color: #fab387; color: #11111b; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_decrypt.clicked.connect(lambda: self.start_process('decrypt'))
        btn_row.addWidget(self.btn_decrypt)
        card_layout.addLayout(btn_row)

        layout.addWidget(self.card)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #45475a; border-radius: 5px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #89b4fa; }
        """)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setHidden(True)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        self.selected_file = None
        self.thread = None

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#eff1f5", "#ccd0da", "#4c4f69", "#1e66f5"
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.desc.setStyleSheet(f"color: {text}; font-size: 14px;")
        self.card.setStyleSheet(f"background-color: {card}; border-radius: 10px; padding: 20px;")
        self.file_label.setStyleSheet(f"color: {text};")
        self.password_input.setStyleSheet(f"background-color: {bg}; color: {text}; padding: 10px; border-radius: 5px; border: 1px solid {card};")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.btn_encrypt.setEnabled(True)
            self.btn_decrypt.setEnabled(True)

    def start_process(self, action):
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Security Key Required", "Please enter a security key (password).")
            return
            
        if not self.selected_file:
            return

        self.btn_encrypt.setEnabled(False)
        self.btn_decrypt.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.password_input.setEnabled(False)
        self.progress_bar.setHidden(False)
        
        self.thread = VaultThread(action, self.selected_file, password)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self, success, message):
        self.progress_bar.setHidden(True)
        self.btn_select.setEnabled(True)
        self.btn_encrypt.setEnabled(True)
        self.btn_decrypt.setEnabled(True)
        self.password_input.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.password_input.clear()
            self.file_label.setText("No file selected")
            self.selected_file = None
        else:
            QMessageBox.critical(self, "Vault Error", message)

    def retranslate(self):
        pass
