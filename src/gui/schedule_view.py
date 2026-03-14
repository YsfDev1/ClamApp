from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QCheckBox, QTimeEdit)
from PyQt6.QtCore import Qt, QTime

class ScheduleView(QWidget):
    def __init__(self, trans, settings_manager, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.settings_manager = settings_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.title = QLabel(self.trans.get("schedule_settings"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        self.card = QFrame()
        self.card.setStyleSheet("background-color: #313244; border-radius: 12px; padding: 20px;")
        card_layout = QVBoxLayout(self.card)

        # Enable checkbox
        self.cb_enable = QCheckBox(self.trans.get("enable_daily_scan"))
        self.cb_enable.setChecked(self.settings_manager.get("daily_scan_enabled", False))
        self.cb_enable.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        card_layout.addWidget(self.cb_enable)

        # Time selection
        time_layout = QHBoxLayout()
        self.lbl_time = QLabel(self.trans.get("scan_time"))
        self.lbl_time.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        time_layout.addWidget(self.lbl_time)

        self.time_edit = QTimeEdit()
        saved_time = self.settings_manager.get("scan_time", "03:00")
        self.time_edit.setTime(QTime.fromString(saved_time, "HH:mm"))
        self.time_edit.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 5px; border-radius: 5px;")
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()
        card_layout.addLayout(time_layout)

        # Save button
        self.btn_save = QPushButton(self.trans.get("save_settings"))
        self.btn_save.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px; margin-top: 10px;")
        self.btn_save.clicked.connect(self.save)
        card_layout.addWidget(self.btn_save)

        layout.addWidget(self.card)
        layout.addStretch()

    def save(self):
        self.settings_manager.set("daily_scan_enabled", self.cb_enable.isChecked())
        self.settings_manager.set("scan_time", self.time_edit.time().toString("HH:mm"))
        # Signal will be handled by the parent to update the scheduler

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#eff1f5", "#ccd0da", "#4c4f69", "#1e66f5"
        
        self.setStyleSheet(f"background-color: {bg}; color: {text};")
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.card.setStyleSheet(f"background-color: {card}; border-radius: 12px; padding: 20px;")
        self.cb_enable.setStyleSheet(f"color: {text}; font-size: 16px;")
        self.lbl_time.setStyleSheet(f"color: {text}; font-size: 16px;")
        self.time_edit.setStyleSheet(f"background-color: {bg}; color: {text}; padding: 5px; border-radius: 5px;")

    def retranslate(self):
        self.title.setText(self.trans.get("schedule_settings"))
        self.cb_enable.setText(self.trans.get("enable_daily_scan"))
        self.lbl_time.setText(self.trans.get("scan_time"))
        self.btn_save.setText(self.trans.get("save_settings"))
