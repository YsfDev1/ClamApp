"""
breach_checker_view.py — Data Breach Checker UI for ClamApp.
Breeze-inspired aesthetic with HIBP integration.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPainter

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.breach_engine import BreachEngine

# ─── Worker thread so the network call doesn't freeze the GUI ───────────────
class BreachCheckThread(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, email: str, provider: str, api_key: str = "", parent=None):
        super().__init__(parent)
        self.email = email
        self.provider = provider
        self.api_key = api_key
        self._engine = BreachEngine()

    def run(self):
        result = self._engine.check_email(self.email, self.provider, self.api_key)
        self.result_ready.emit(result)


# ─── Breach card widget ───────────────────────────────────────────────────────
class BreachCard(QFrame):
    def __init__(self, breach: dict, c: dict, parent=None):
        super().__init__(parent)
        self._setup(breach, c)

    def _setup(self, b: dict, c: dict):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['card']};
                border-radius: 12px;
                border-left: 4px solid #f38ba8;
                padding: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        title_lbl = QLabel(f"🔓 {b['title']}")
        title_lbl.setStyleSheet(f"color: #f38ba8; font-size: 15px; font-weight: bold; border: none;")
        header.addWidget(title_lbl)
        header.addStretch()

        date_lbl = QLabel(b["date"])
        date_lbl.setStyleSheet(f"color: {c['muted']}; font-size: 11px; border: none;")
        header.addWidget(date_lbl)
        layout.addLayout(header)

        if b["domain"]:
            domain_lbl = QLabel(f"🌐 {b['domain']}")
            domain_lbl.setStyleSheet(f"color: {c['subtext']}; font-size: 12px; border: none;")
            layout.addWidget(domain_lbl)

        if b["data_classes"]:
            data_str = ", ".join(b["data_classes"][:5])
            if len(b["data_classes"]) > 5:
                data_str += f" +{len(b['data_classes']) - 5} more"
            dc_lbl = QLabel(f"📋 Exposed: {data_str}")
            dc_lbl.setStyleSheet(f"color: {c['orange']}; font-size: 12px; border: none;")
            dc_lbl.setWordWrap(True)
            layout.addWidget(dc_lbl)

        if b["description"]:
            desc = b["description"][:180] + ("…" if len(b["description"]) > 180 else "")
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {c['subtext']}; font-size: 12px; border: none;")
            desc_lbl.setWordWrap(True)
            layout.addWidget(desc_lbl)


# ─── Main Breach Checker View ─────────────────────────────────────────────────
class BreachCheckerView(QWidget):
    def __init__(self, trans, settings_manager, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.settings_manager = settings_manager
        self.is_dark = True
        self._thread = None
        self._init_ui()

    # ── Color theme shortcut ─────────────────────────────────────────────────
    @property
    def _c(self):
        if self.is_dark:
            return {
                "bg": "#181825", "card": "#313244", "card2": "#45475a",
                "text": "#cdd6f4", "subtext": "#bac2de", "muted": "#585b70",
                "accent": "#89b4fa", "green": "#a6e3a1", "red": "#f38ba8",
                "orange": "#fab387", "sidebar": "#1e1e2e",
            }
        else:
            return {
                "bg": "#eff1f5", "card": "#e6e9ef", "card2": "#ccd0da",
                "text": "#4c4f69", "subtext": "#6c6f85", "muted": "#9ca0b0",
                "accent": "#1e66f5", "green": "#40a02b", "red": "#d20f39",
                "orange": "#fe640b", "sidebar": "#dce0e8",
            }

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header
        header = QVBoxLayout()
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa;")
        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setStyleSheet("font-size: 14px; color: #585b70;")
        header.addWidget(self.title_lbl)
        header.addWidget(self.subtitle_lbl)
        layout.addLayout(header)

        # Input Card
        self.input_card = QFrame()
        self.input_card.setObjectName("inputCard")
        self.input_card.setMinimumHeight(180)
        card_layout = QVBoxLayout(self.input_card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        self.email_label = QLabel()
        self.email_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        card_layout.addWidget(self.email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setMinimumHeight(50)
        self.email_input.returnPressed.connect(self._on_check_clicked)
        card_layout.addWidget(self.email_input)

        self.check_btn = QPushButton()
        self.check_btn.setMinimumHeight(55)
        self.check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_btn.clicked.connect(self._on_check_clicked)
        card_layout.addWidget(self.check_btn)

        layout.addWidget(self.input_card)

        # Warning Message for missing key
        self.key_warning = QLabel()
        self.key_warning.setStyleSheet("color: #fab387; font-size: 13px; font-weight: bold;")
        self.key_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_warning.setWordWrap(True)
        self.key_warning.hide()
        layout.addWidget(self.key_warning)

        # Status Frame
        self.status_frame = QFrame()
        self.status_frame.setObjectName("statusFrame")
        self.status_frame.hide()
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(20, 15, 20, 15)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedWidth(40)
        self.status_icon.setStyleSheet("font-size: 24px;")
        status_layout.addWidget(self.status_icon)
        
        self.status_msg = QLabel()
        self.status_msg.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.status_msg)
        
        layout.addWidget(self.status_frame)

        # Results Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.retranslate()
        self.apply_theme(self.is_dark)

    # ── States ───────────────────────────────────────────────────────────────
    def _set_idle_state(self):
        self.status_frame.hide()

    def _set_loading_state(self):
        self.status_frame.show()
        self.status_icon.setText("⏳")
        provider_name = self._provider_display_name()
        msg = (self.trans.get("breach_searching_via") or "Searching via {provider}...").format(provider=provider_name)
        self.status_msg.setText(msg)
        self.status_frame.setStyleSheet(f"""
            QFrame {{ background-color: {self._c['card']}; border-radius: 14px; }}
        """)
        self.status_msg.setStyleSheet(f"color: {self._c['accent']}; font-size: 16px; font-weight: bold;")
        self._clear_cards()

    def _set_safe_state(self):
        self.status_frame.show()
        self.status_icon.setText("✅")
        self.status_msg.setText(self.trans.get("breach_safe") or "Your Data is Safe!")
        c = self._c
        self.status_frame.setStyleSheet(f"""
            QFrame {{ background-color: #1a2e1a; border-radius: 14px; border: 2px solid {c['green']}; }}
        """)
        self.status_msg.setStyleSheet(f"color: {c['green']}; font-size: 18px; font-weight: bold;")
        self._clear_cards()

    def _set_breached_state(self, count: int):
        self.status_frame.show()
        self.status_icon.setText("🚨")
        msg = (self.trans.get("breach_alert") or "Security Alert!") + f"  —  {count} breach(es) found"
        self.status_msg.setText(msg)
        c = self._c
        self.status_frame.setStyleSheet(f"""
            QFrame {{ background-color: #2e1a1a; border-radius: 14px; border: 2px solid {c['red']}; }}
        """)
        self.status_msg.setStyleSheet(f"color: {c['red']}; font-size: 18px; font-weight: bold;")

    def _set_error_state(self, message: str):
        self.status_frame.show()
        self.status_icon.setText("⚠️")
        self.status_msg.setText(message)
        c = self._c
        self.status_frame.setStyleSheet(f"""
            QFrame {{ background-color: #2e250a; border-radius: 14px; border: 2px solid {c['orange']}; }}
        """)
        self.status_msg.setStyleSheet(f"color: {c['orange']}; font-size: 15px; font-weight: bold;")
        self._clear_cards()

    # ── Logic ────────────────────────────────────────────────────────────────
    def _on_check_clicked(self):
        email = self.email_input.text().strip()
        if not email: return

        provider = (self.settings_manager.get("breach_provider", "bd") or "bd").strip().lower()
        key_field = "bd_api_key" if provider == "bd" else "hibp_api_key"
        key = (self.settings_manager.get(key_field, "") or "").strip()
        if not key:
            prov_name = self._provider_display_name(provider)
            msg = (self.trans.get("breach_no_key_for_provider") or
                   "No API Key found. Please configure your {provider} key in Settings.").format(provider=prov_name)
            self._set_error_state(msg)
            return

        if self._thread and self._thread.isRunning():
            return

        self.check_btn.setEnabled(False)
        self._set_loading_state()

        try:
            self._thread = BreachCheckThread(email, provider, key, parent=self)
            self._thread.result_ready.connect(self._on_result_ready)
            self._thread.start()
        except Exception as exc:
            self._set_error_state(str(exc))

    def _on_result_ready(self, result: dict):
        self.check_btn.setEnabled(True)
        status = result["status"]

        if status == "safe":
            self._set_safe_state()
        elif status == "breached":
            breaches = result["breaches"]
            self._set_breached_state(len(breaches))
            self._populate_cards(breaches)
        else:
            msg_key = result.get("message", "unexpected_error")
            self._set_error_state(self._map_engine_message(msg_key))

    def _map_engine_message(self, msg_key: str) -> str:
        mapping = {
            "invalid_key": self.trans.get("breach_err_invalid_key"),
            "rate_limited": self.trans.get("breach_err_rate_limited"),
            "network_error": self.trans.get("breach_err_network"),
            "http_error": self.trans.get("breach_err_http"),
            "unexpected_error": self.trans.get("breach_err_unexpected"),
            "no_key": self.trans.get("breach_err_no_key"),
        }
        return mapping.get(msg_key, self.trans.get("breach_err_unexpected"))

    def _provider_display_name(self, provider: str | None = None) -> str:
        provider = (provider or self.settings_manager.get("breach_provider", "bd") or "bd").strip().lower()
        return self.trans.get("provider_bd") if provider == "bd" else self.trans.get("provider_hibp")

    def _clear_cards(self):
        while self.cards_layout.count() > 1:  # keep the final stretch
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _populate_cards(self, breaches: list):
        self._clear_cards()
        c = self._c
        for breach in breaches:
            card = BreachCard(breach, c)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ── Theme ────────────────────────────────────────────────────────────────
    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = self._c
        self.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']};")
        
        self.title_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {c['accent']};")
        self.subtitle_lbl.setStyleSheet(f"font-size: 14px; color: {c['muted']};")
        
        self.input_card.setStyleSheet(f"""
            #inputCard {{
                background-color: {c['card']};
                border-radius: 18px;
                border: 2px solid {c['card2']};
            }}
            QLineEdit {{
                background-color: {c['bg']};
                color: {c['text']};
                border: 2px solid {c['card2']};
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c['accent']}, stop:1 #3dd0f5);
                color: #11111b;
                border-radius: 12px;
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a0c4ff, stop:1 {c['accent']});
            }}
        """)
        
        self.key_warning.setStyleSheet(f"color: {c['orange']}; font-size: 13px; font-weight: bold;")
        
        self.email_label.setStyleSheet(f"color: {c['subtext']}; font-size: 15px; font-weight: bold;")
        
        # Cards in results
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                if hasattr(item.widget(), "apply_theme"):
                    item.widget().apply_theme(c)

    def retranslate(self):
        self.title_lbl.setText(self.trans.get("breach_checker"))
        self.subtitle_lbl.setText(self.trans.get("breach_subtitle"))
        self.email_label.setText(self.trans.get("breach_email_label"))
        self.check_btn.setText(self.trans.get("breach_check_btn"))
        # Dynamic warning based on provider + key presence
        provider = (self.settings_manager.get("breach_provider", "bd") or "bd").strip().lower()
        key_field = "bd_api_key" if provider == "bd" else "hibp_api_key"
        key = (self.settings_manager.get(key_field, "") or "").strip()
        prov_name = self._provider_display_name(provider)
        self.key_warning.setText(
            (self.trans.get("breach_no_key_for_provider") or
             "No API Key found. Please configure your {provider} key in Settings.").format(provider=prov_name)
        )
        self.key_warning.setVisible(not bool(key))
