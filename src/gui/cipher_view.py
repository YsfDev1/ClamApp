from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QSpinBox, QFrame, QComboBox)
from PyQt6.QtCore import Qt


class CipherView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, inp, accent = "#181825", "#313244", "#cdd6f4", "#1e1e2e", "#89b4fa"
        else:
            bg, card, text, inp, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#ffffff", "#1e66f5"
        self.setAutoFillBackground(True)
        p = self.palette()
        from PyQt6.QtGui import QColor
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.control_frame.setStyleSheet(f"background-color: {inp}; border: 1px solid {'#313244' if dark else '#c0c0cc'}; border-radius: 10px; padding: 15px;")
        self.lbl_shift.setStyleSheet(f"color: {text};")
        self.lbl_method.setStyleSheet(f"color: {text};")
        self.input_text.setStyleSheet(f"background-color: {card}; color: {text}; border-radius: 8px; padding: 10px;")
        self.output_text.setStyleSheet(f"background-color: {card}; color: {accent}; border-radius: 8px; padding: 10px;")
        self.note_label.setStyleSheet("color: #f38ba8; font-style: italic; font-size: 11px;")
        self.spin_shift.setStyleSheet(f"background-color: {card}; color: {text}; padding: 5px;")
        self.combo_method.setStyleSheet(f"background-color: {card}; color: {text}; padding: 5px;")
        self.lbl_key.setStyleSheet(f"color: {text};")
        self.key_input.setStyleSheet(f"background-color: {card}; color: {text}; padding: 5px; border-radius: 4px;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel(self.trans.get("cipher_tool"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        # Input
        self.lbl_input = QLabel(self.trans.get("message"))
        self.lbl_input.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(self.lbl_input)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter message here...")
        self.input_text.setStyleSheet("background-color: #313244; color: #cdd6f4; border-radius: 8px; padding: 10px;")
        layout.addWidget(self.input_text)

        # Controls
        self.control_frame = QFrame()
        self.control_frame.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; padding: 15px;")
        ctrl = QVBoxLayout(self.control_frame)

        row1 = QHBoxLayout()
        self.lbl_method = QLabel(self.trans.get("cipher_method"))
        self.lbl_method.setStyleSheet("color: #cdd6f4;")
        row1.addWidget(self.lbl_method)

        self.combo_method = QComboBox()
        self.combo_method.addItems([
            "Caesar", "ROT-13", "Atbash", "Vigenere", "Rail Fence"
        ])
        self.combo_method.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        self.combo_method.currentTextChanged.connect(self.on_method_changed)
        row1.addWidget(self.combo_method)
        ctrl.addLayout(row1)

        self.shift_row = QHBoxLayout()
        self.lbl_shift = QLabel(self.trans.get("shift"))
        self.lbl_shift.setStyleSheet("color: #cdd6f4;")
        self.shift_row.addWidget(self.lbl_shift)

        self.spin_shift = QSpinBox()
        self.spin_shift.setRange(1, 25)
        self.spin_shift.setValue(3)
        self.spin_shift.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        self.shift_row.addWidget(self.spin_shift)
        ctrl.addLayout(self.shift_row)

        self.key_row = QHBoxLayout()
        self.lbl_key = QLabel(self.trans.get("vigenere_key"))
        self.lbl_key.setStyleSheet("color: #cdd6f4;")
        self.key_row.addWidget(self.lbl_key)

        from PyQt6.QtWidgets import QLineEdit
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g. SECRET")
        self.key_input.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px; border-radius: 4px;")
        self.key_row.addWidget(self.key_input)
        ctrl.addLayout(self.key_row)

        btn_row = QHBoxLayout()
        self.btn_encrypt = QPushButton(self.trans.get("encrypt"))
        self.btn_encrypt.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_encrypt.clicked.connect(self.encrypt_message)
        btn_row.addWidget(self.btn_encrypt)

        self.btn_decrypt = QPushButton(self.trans.get("decrypt"))
        self.btn_decrypt.setStyleSheet("background-color: #fab387; color: #11111b; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_decrypt.clicked.connect(self.decrypt_message)
        btn_row.addWidget(self.btn_decrypt)
        ctrl.addLayout(btn_row)

        layout.addWidget(self.control_frame)

        # Security Note
        self.note_label = QLabel(self.trans.get("cipher_note"))
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("color: #f38ba8; font-style: italic; font-size: 11px;")
        layout.addWidget(self.note_label)

        # Output
        self.lbl_result = QLabel(self.trans.get("result"))
        self.lbl_result.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(self.lbl_result)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #313244; color: #89b4fa; border-radius: 8px; padding: 10px;")
        layout.addWidget(self.output_text)

        # Initial state
        self.on_method_changed("Caesar")

    def on_method_changed(self, method):
        caesar_like = method in ("Caesar",)
        vigenere_like = method in ("Vigenere",)
        rail_like = method in ("Rail Fence",)
        no_key = method in ("ROT-13", "Atbash")

        for w in [self.lbl_shift, self.spin_shift]:
            w.setVisible(caesar_like or rail_like)
        for w in [self.lbl_key, self.key_input]:
            w.setVisible(vigenere_like)

        if rail_like:
            self.spin_shift.setRange(2, 10)
            self.lbl_shift.setText(self.trans.get("rails"))
        else:
            self.spin_shift.setRange(1, 25)
            self.lbl_shift.setText(self.trans.get("shift"))

    # ── Cipher Algorithms ────────────────────────────────────────────────────

    def _caesar(self, text, shift, decrypt=False):
        if decrypt: shift = -shift
        result = ""
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                result += chr((ord(ch) - base + shift) % 26 + base)
            else:
                result += ch
        return result

    def _rot13(self, text):
        return self._caesar(text, 13)

    def _atbash(self, text):
        result = ""
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                result += chr(base + (25 - (ord(ch) - base)))
            else:
                result += ch
        return result

    def _vigenere(self, text, key, decrypt=False):
        if not key:
            return text
        key = key.upper()
        result = ""
        ki = 0
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                k = ord(key[ki % len(key)]) - ord('A')
                if decrypt: k = -k
                result += chr((ord(ch) - base + k) % 26 + base)
                ki += 1
            else:
                result += ch
        return result

    def _rail_fence(self, text, rails, decrypt=False):
        if rails < 2:
            return text
        if not decrypt:
            fence = [[] for _ in range(rails)]
            rail, direction = 0, 1
            for ch in text:
                fence[rail].append(ch)
                if rail == 0: direction = 1
                elif rail == rails - 1: direction = -1
                rail += direction
            return "".join(ch for row in fence for ch in row)
        else:
            n = len(text)
            pattern = []
            rail, direction = 0, 1
            for i in range(n):
                pattern.append(rail)
                if rail == 0: direction = 1
                elif rail == rails - 1: direction = -1
                rail += direction
            order = sorted(range(n), key=lambda i: pattern[i])
            result = [''] * n
            for idx, ch in zip(order, text):
                result[idx] = ch
            return "".join(result)

    # ── Encrypt / Decrypt ─────────────────────────────────────────────────────

    def _process(self, decrypt=False):
        text = self.input_text.toPlainText()
        method = self.combo_method.currentText()
        if method == "Caesar":
            return self._caesar(text, self.spin_shift.value(), decrypt)
        elif method == "ROT-13":
            return self._rot13(text)   # ROT-13 is its own inverse
        elif method == "Atbash":
            return self._atbash(text)  # Atbash is its own inverse
        elif method == "Vigenere":
            return self._vigenere(text, self.key_input.text(), decrypt)
        elif method == "Rail Fence":
            return self._rail_fence(text, self.spin_shift.value(), decrypt)
        return text

    def encrypt_message(self):
        self.output_text.setPlainText(self._process(decrypt=False))

    def decrypt_message(self):
        self.output_text.setPlainText(self._process(decrypt=True))

    def retranslate(self):
        self.title.setText(self.trans.get("cipher_tool"))
        self.note_label.setText(self.trans.get("cipher_note"))
        self.btn_encrypt.setText(self.trans.get("encrypt"))
        self.btn_decrypt.setText(self.trans.get("decrypt"))
        self.lbl_input.setText(self.trans.get("message"))
        self.lbl_result.setText(self.trans.get("result"))
        self.lbl_method.setText(self.trans.get("cipher_method"))
        self.lbl_key.setText(self.trans.get("vigenere_key"))
        self.on_method_changed(self.combo_method.currentText())
