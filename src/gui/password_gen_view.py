import random
import string
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QCheckBox, QLineEdit, QFrame,
                             QApplication)
from PyQt6.QtCore import Qt


class PasswordGeneratorView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.init_ui()

    def _style(self, dark=True):
        if dark:
            return {
                "bg": "#181825", "card": "#313244", "border": "#45475a",
                "text": "#cdd6f4", "input": "#1e1e2e"
            }
        else:
            return {
                "bg": "#f2f2f5", "card": "#e0e0e8", "border": "#c0c0cc",
                "text": "#1e1e2e", "input": "#ffffff"
            }

    def apply_theme(self, dark=True):
        c = self._style(dark)
        self.setAutoFillBackground(True)
        p = self.palette()
        from PyQt6.QtGui import QColor
        p.setColor(self.backgroundRole(), QColor(c["bg"]))
        self.setPalette(p)
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {'#89b4fa' if dark else '#1e66f5'};")
        self.display_frame.setStyleSheet(f"background-color: {c['card']}; border-radius: 10px; padding: 10px;")
        self.password_display.setStyleSheet(f"background-color: transparent; border: none; color: {'#89b4fa' if dark else '#1e66f5'}; font-size: 18px; font-family: monospace;")
        self.btn_copy.setStyleSheet(f"background-color: {c['border']}; color: {c['text']}; border-radius: 5px; padding: 8px 15px;")
        self.options_frame.setStyleSheet(f"background-color: {c['input']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 15px;")
        self.label_length.setStyleSheet(f"color: {c['text']};")
        for cb in [self.check_upper, self.check_numbers, self.check_special]:
            cb.setStyleSheet(f"color: {c['text']};")
        self.label_seed.setStyleSheet(f"color: {c['text']};")
        self.seed_input.setStyleSheet(f"background-color: {c['card']}; color: {c['text']}; border-radius: 5px; padding: 8px;")
        if not self.strength_label.styleSheet().startswith("color: #f") and not self.strength_label.styleSheet().startswith("color: #a"):
            self.strength_label.setStyleSheet(f"color: {c['text']};")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel(self.trans.get("password_gen"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        # Password Display
        self.display_frame = QFrame()
        self.display_frame.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 10px;")
        display_layout = QHBoxLayout(self.display_frame)

        self.password_display = QLineEdit()
        self.password_display.setReadOnly(True)
        self.password_display.setStyleSheet("background-color: transparent; border: none; color: #89b4fa; font-size: 18px; font-family: monospace;")
        display_layout.addWidget(self.password_display)

        self.btn_copy = QPushButton(self.trans.get("copy"))
        self.btn_copy.setStyleSheet("background-color: #45475a; color: #cdd6f4; border-radius: 5px; padding: 8px 15px;")
        self.btn_copy.clicked.connect(self.copy_password)
        display_layout.addWidget(self.btn_copy)

        layout.addWidget(self.display_frame)

        # Strength Indicator
        self.strength_label = QLabel(f"{self.trans.get('strength')}: -")
        self.strength_label.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.strength_label)

        # Options
        self.options_frame = QFrame()
        self.options_frame.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; padding: 15px;")
        options_layout = QVBoxLayout(self.options_frame)

        # Length Slider
        len_layout = QHBoxLayout()
        self.label_length = QLabel(f"{self.trans.get('length')}: 16")
        self.label_length.setStyleSheet("color: #cdd6f4;")
        len_layout.addWidget(self.label_length)

        self.slider_length = QSlider(Qt.Orientation.Horizontal)
        self.slider_length.setRange(8, 64)
        self.slider_length.setValue(16)
        self.slider_length.valueChanged.connect(self.update_length_label)
        len_layout.addWidget(self.slider_length)
        options_layout.addLayout(len_layout)

        self.check_upper = QCheckBox(self.trans.get("uppercase"))
        self.check_upper.setChecked(True)
        self.check_upper.setStyleSheet("color: #cdd6f4;")
        options_layout.addWidget(self.check_upper)

        self.check_numbers = QCheckBox(self.trans.get("numbers"))
        self.check_numbers.setChecked(True)
        self.check_numbers.setStyleSheet("color: #cdd6f4;")
        options_layout.addWidget(self.check_numbers)

        self.check_special = QCheckBox(self.trans.get("special"))
        self.check_special.setChecked(True)
        self.check_special.setStyleSheet("color: #cdd6f4;")
        options_layout.addWidget(self.check_special)

        # Seed Words - kept INTACT as complete words
        self.label_seed = QLabel(self.trans.get("seed_words"))
        self.label_seed.setStyleSheet("color: #cdd6f4; margin-top: 10px;")
        options_layout.addWidget(self.label_seed)

        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("e.g. Pardus, 2026")
        self.seed_input.setStyleSheet("background-color: #313244; color: #cdd6f4; border-radius: 5px; padding: 8px;")
        options_layout.addWidget(self.seed_input)

        layout.addWidget(self.options_frame)

        self.btn_generate = QPushButton(self.trans.get("generate"))
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
                padding: 15px;
            }
            QPushButton:hover { background-color: #b4befe; }
        """)
        self.btn_generate.clicked.connect(self.generate_password)
        layout.addWidget(self.btn_generate)

        layout.addStretch()

    def update_length_label(self, value):
        self.label_length.setText(f"{self.trans.get('length')}: {value}")

    def generate_password(self):
        length = self.slider_length.value()
        chars = string.ascii_lowercase
        if self.check_upper.isChecked():
            chars += string.ascii_uppercase
        if self.check_numbers.isChecked():
            chars += string.digits
        if self.check_special.isChecked():
            chars += string.punctuation

        rng = random.SystemRandom()
        seed_text = self.seed_input.text().strip()

        if seed_text:
            # FIX: Seed words are kept INTACT (not shuffled char-by-char).
            # We collect the full words, then surround/intersperse with random chars.
            words = [w.strip() for w in seed_text.split(',') if w.strip()]
            combined = "".join(words)  # e.g. "Joseph2026"

            if len(combined) >= length:
                # If seeds already fill the length, just use them
                password = combined[:length]
            else:
                # Insert random characters between and around the seed words
                remaining = length - len(combined)
                random_chars = [rng.choice(chars) for _ in range(remaining)]

                # Build password: random chars before, the word, random chars after, etc.
                result = []
                random_idx = 0
                chars_per_gap = remaining // (len(words) + 1)

                for i, word in enumerate(words):
                    # Prepend random chars before each word
                    gap = chars_per_gap if i < len(words) - 1 else len(random_chars) - random_idx
                    for j in range(chars_per_gap):
                        if random_idx < len(random_chars):
                            result.append(random_chars[random_idx])
                            random_idx += 1
                    result.append(word)  # word stays intact

                # Append remaining random chars at the end
                while random_idx < len(random_chars):
                    result.append(random_chars[random_idx])
                    random_idx += 1

                password = "".join(result)
        else:
            password = "".join(rng.choice(chars) for _ in range(length))

        self.password_display.setText(password)
        self.update_strength(password)

    def update_strength(self, password):
        score = 0
        if len(password) >= 12: score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in string.punctuation for c in password): score += 1

        if score <= 1:
            text, color = self.trans.get("weak"), "#f38ba8"
        elif score <= 3:
            text, color = self.trans.get("medium"), "#fab387"
        else:
            text, color = self.trans.get("strong"), "#a6e3a1"

        self.strength_label.setText(f"{self.trans.get('strength')}: {text}")
        self.strength_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def copy_password(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.password_display.text())

    def retranslate(self):
        self.title.setText(self.trans.get("password_gen"))
        self.btn_copy.setText(self.trans.get("copy"))
        self.update_length_label(self.slider_length.value())
        self.check_upper.setText(self.trans.get("uppercase"))
        self.check_numbers.setText(self.trans.get("numbers"))
        self.check_special.setText(self.trans.get("special"))
        self.label_seed.setText(self.trans.get("seed_words"))
        self.btn_generate.setText(self.trans.get("generate"))
        if self.password_display.text():
            self.update_strength(self.password_display.text())
        else:
            self.strength_label.setText(f"{self.trans.get('strength')}: -")
