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

        self.title = QLabel(self.trans.get("crypto_vault"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        self.desc = QLabel(self.trans.get("vault_desc") if self.trans.get("vault_desc") != "vault_desc" else "Securely encrypt or decrypt any file. Use a strong password to protect your data.")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        layout.addWidget(self.desc)

        # Main card
        self.card = QFrame()
        self.card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px;")
        card_layout = QVBoxLayout(self.card)

        # File selection
        file_row = QHBoxLayout()
        self.btn_select = QPushButton(self.trans.get("select_file"))
        self.btn_select.setStyleSheet("background-color: #45475a; color: #cdd6f4; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_select.clicked.connect(self.select_file)
        file_row.addWidget(self.btn_select)

        self.file_label = QLabel(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
        self.file_label.setStyleSheet("color: #bac2de;")
        file_row.addWidget(self.file_label, 1)
        card_layout.addLayout(file_row)

        # Password input
        self.lbl_key = QLabel(self.trans.get("security_key"))
        card_layout.addWidget(self.lbl_key)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.trans.get("key_placeholder") if self.trans.get("key_placeholder") != "key_placeholder" else "Enter encryption/decryption key...")
        self.password_input.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 10px; border-radius: 5px; border: 1px solid #45475a;")
        card_layout.addWidget(self.password_input)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_encrypt = QPushButton(self.trans.get("encrypt"))
        self.btn_encrypt.setEnabled(False)
        self.btn_encrypt.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_encrypt.clicked.connect(lambda: self.start_process('encrypt'))
        btn_row.addWidget(self.btn_encrypt)

        self.btn_decrypt = QPushButton(self.trans.get("decrypt"))
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
        file_path, _ = QFileDialog.getOpenFileName(self, self.trans.get("select_file"))
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.btn_encrypt.setEnabled(True)
            self.btn_decrypt.setEnabled(True)

    def start_process(self, action):
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, self.trans.get("key_required"), self.trans.get("key_required_msg"))
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
            QMessageBox.information(self, self.trans.get("success") if self.trans.get("success") != "success" else "Success", message)
            self.password_input.clear()
            self.file_label.setText(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
            self.selected_file = None
        else:
            QMessageBox.critical(self, self.trans.get("vault_error") if self.trans.get("vault_error") != "vault_error" else "Vault Error", message)

    def retranslate(self):
        self.title.setText(self.trans.get("crypto_vault"))
        self.desc.setText(self.trans.get("vault_desc") if self.trans.get("vault_desc") != "vault_desc" else "Securely encrypt or decrypt any file. Use a strong password to protect your data.")
        self.btn_select.setText(self.trans.get("select_file"))
        self.lbl_key.setText(self.trans.get("security_key"))
        self.password_input.setPlaceholderText(self.trans.get("key_placeholder") if self.trans.get("key_placeholder") != "key_placeholder" else "Enter encryption/decryption key...")
        self.btn_encrypt.setText(self.trans.get("encrypt"))
        self.btn_decrypt.setText(self.trans.get("decrypt"))
        if not self.selected_file:
            self.file_label.setText(self.trans.get("no_file_selected") if self.trans.get("no_file_selected") != "no_file_selected" else "No file selected")
        else:
            self.file_label.setText(os.path.basename(self.selected_file))

