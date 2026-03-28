"""
firewall_view.py — Dual-mode Firewall UI for ClamApp.

Basic Protection:
  - big shield toggle + quick profiles (Home / Public / Kill-Switch)

Advanced Console:
  - numbered rules table + add/delete rules
  - live log stream for /var/log/ufw.log

All privileged operations run off the UI thread via QThreads.
"""

import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QMessageBox, QSizePolicy, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox, QPlainTextEdit, QSplitter,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QDateTime
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QTextCursor

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.firewall_manager import FirewallManagerBackend


# ─── Loading Spinner ───────────────────────────────────────────────────────
class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._color = "#89b4fa"

    def start(self):
        self._timer.start(50)

    def stop(self):
        self._timer.stop()

    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(12, 12)
        painter.rotate(self._angle)
        
        pen = QPen(QColor(self._color), 3)
        painter.setPen(pen)
        painter.drawArc(-8, -8, 16, 16, 0, 270)

# ─── Pulsing indicator dot ────────────────────────────────────────────────────
class PulsingDot(QWidget):
    """A small circle that pulses via opacity animation."""

    def __init__(self, color: str = "#a6e3a1", parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._color = QColor(color)
        self._opacity = 1.0
        self._anim = QPropertyAnimation(self, b"dot_opacity")
        self._anim.setDuration(1200)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.3)
        self._anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)
        self.update()

    def get_dot_opacity(self) -> float:
        return self._opacity

    def set_dot_opacity(self, val: float):
        self._opacity = val
        self.update()

    dot_opacity = pyqtProperty(float, get_dot_opacity, set_dot_opacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)
        color = self._color
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)


# ─── Worker threads ───────────────────────────────────────────────────────────
class StatusThread(QThread):
    status_ready = pyqtSignal(dict)

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self._backend = backend

    def run(self):
        self.status_ready.emit(self._backend.get_status())


class ToggleThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, backend, enable: bool, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._enable = enable

    def run(self):
        self.done.emit(self._backend.set_enabled(self._enable))


class ProfileThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, backend, profile: str, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._profile = profile

    def run(self):
        self.done.emit(self._backend.apply_profile(self._profile))


class RulesThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self._backend = backend

    def run(self):
        self.done.emit(self._backend.get_rules_numbered())


class DeleteRuleThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, backend, rule_id: int, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._rule_id = rule_id

    def run(self):
        self.done.emit(self._backend.delete_rule(self._rule_id))


class AddRuleThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, backend, action: str, direction: str, port: str, protocol: str, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._action = action
        self._direction = direction
        self._port = port
        self._protocol = protocol

    def run(self):
        self.done.emit(self._backend.add_rule(self._action, self._direction, self._port, self._protocol))


class LogTailThread(QThread):
    line_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, log_path: str = None, parent=None):
        super().__init__(parent)
        # Use cross-distro compatible log path
        if log_path is None:
            # Check common UFW log locations
            possible_paths = [
                "/var/log/ufw.log",
                "/var/log/ufw.log.1",  # Some systems use rotated logs
                "/var/log/kern.log",  # Fallback for systems without UFW logging
            ]
            log_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    log_path = path
                    break
            # Default to standard path if none found
            if log_path is None:
                log_path = "/var/log/ufw.log"
        
        self._log_path = log_path
        self._running = True
        self._proc = None
        self._retry_count = 0
        self._max_retries = 3

    def stop(self):
        self._running = False
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                self._proc.wait(timeout=2)
        except Exception:
            pass

    def run(self):
        while self._running and self._retry_count < self._max_retries:
            try:
                if not os.path.exists(self._log_path):
                    self.error.emit("missing")
                    return

                # Use pkexec tail -f for persistent log streaming
                # With Polkit policy, this should only prompt once per session
                cmd = ["pkexec", "tail", "-n", "200", "-f", self._log_path]
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Read stdout line-by-line
                while self._running and self._proc.poll() is None:
                    line = self._proc.stdout.readline() if self._proc.stdout else ""
                    if not line:
                        self.msleep(200)
                        continue
                    self.line_ready.emit(line.rstrip("\n"))
                    self._retry_count = 0  # Reset retry count on successful read

                # Check if process exited due to authentication failure
                if self._proc.returncode != 0 and self._running:
                    stderr = self._proc.stderr.read() if self._proc.stderr else ""
                    if "Permission denied" in stderr or "cancelled" in stderr.lower():
                        self.error.emit("permission")
                        return
                    else:
                        self._retry_count += 1
                        self.msleep(2000)  # Wait before retry
                        continue

            except PermissionError:
                self.error.emit("permission")
                return
            except Exception as exc:
                self._retry_count += 1
                if self._retry_count >= self._max_retries:
                    self.error.emit(str(exc))
                    return
                self.msleep(3000)  # Wait before retry


class InstallUfwThread(QThread):
    done = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            cmd = ["pkexec", "apt", "install", "-y", "ufw"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            proc.wait(timeout=60)  # Wait up to 60 seconds for installation
            self.done.emit(True)
        except Exception:
            self.done.emit(False)

# ─── Master Toggle Button ─────────────────────────────────────────────────────
class MasterToggleButton(QPushButton):
    """Large glowing toggle button for firewall enable/disable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._loading = False
        self._spinner = LoadingSpinner(self)
        self._spinner.move(68, 68)
        self._spinner.hide()
        
        # Add glow effect
        self._glow_effect = QGraphicsDropShadowEffect(self)
        self._glow_effect.setBlurRadius(20)
        self._glow_effect.setColor(QColor("#40a02b"))
        self._glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self._glow_effect)
        self._glow_effect.setEnabled(False)
        
        self._update_style(False)

    def set_loading(self, loading: bool):
        """Show/hide loading spinner and disable/enable button."""
        self._loading = loading
        if loading:
            self._spinner.start()
            self._spinner.show()
            self.setEnabled(False)
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #89b4fa, stop:1 #45475a);
                    border-radius: 80px;
                    border: 4px solid #89b4fa;
                    color: #cdd6f4;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            self.setText("⏳\nLoading")
        else:
            self._spinner.stop()
            self._spinner.hide()
            self.setEnabled(True)
            self._update_style(self.isChecked())

    def _update_style(self, enabled: bool):
        if self._loading:
            return  # Don't change style while loading
            
        # Control glow effect
        if enabled:
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor("#40a02b"))  # Green glow for active
        else:
            self._glow_effect.setEnabled(False)  # No glow when inactive
            
        if enabled:
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #a6e3a1, stop:1 #40a02b);
                    border-radius: 80px;
                    border: 4px solid #a6e3a1;
                    color: #11111b;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 4px solid #b8f0b3;
                }
            """)
            self.setText("🛡\nON")
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #585b70, stop:1 #313244);
                    border-radius: 80px;
                    border: 4px solid #45475a;
                    color: #585b70;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 4px solid #89b4fa;
                }
            """)
            self.setText("🔓\nOFF")

    def set_enabled_state(self, enabled: bool):
        self.blockSignals(True)
        self.setChecked(enabled)
        self.blockSignals(False)
        self._update_style(enabled)


# ─── Profile Button ────────────────────────────────────────────────────────────
class ProfileButton(QPushButton):
    def __init__(self, name: str, icon: str, desc: str, c: dict, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_name = name
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._icon = icon
        self._desc = desc
        self._name = name.capitalize()
        self._c = c
        self._refresh_style(False)

    def _refresh_style(self, checked: bool):
        c = self._c
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1e3a5f;
                    border-radius: 12px;
                    border: 2px solid {c['accent']};
                    color: {c['accent']};
                    font-size: 13px;
                    font-weight: bold;
                    padding: 12px;
                    text-align: left;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card']};
                    border-radius: 12px;
                    border: 2px solid transparent;
                    color: {c['text']};
                    font-size: 13px;
                    padding: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    border-color: {c['accent']};
                }}
            """)
        self.setText(f"{self._icon}  {self._name}\n     {self._desc}")

    def set_theme(self, c: dict):
        self._c = c
        self._refresh_style(self.isChecked())

    def nextCheckState(self):
        # Only allow checking, not unchecking via click
        if not self.isChecked():
            self.setChecked(True)
            self._refresh_style(True)


class ModePill(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def apply_style(self, c: dict):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['card']};
                color: {c['text']};
                border: 2px solid {c['card2']};
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: bold;
                min-width: 160px;
            }}
            QPushButton:checked {{
                background-color: {c['accent']};
                color: #11111b;
                border-color: {c['accent']};
            }}
            QPushButton:hover {{
                border-color: {c['accent']};
            }}
        """)


class AddRuleDialog(QDialog):
    def __init__(self, trans, c: dict, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.c = c
        self.setWindowTitle(self.trans.get("fw_add_rule"))
        self.setModal(True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {c['card']}; border-radius: 14px; border: 2px solid {c['card2']}; }}")
        root.addWidget(card)
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        self.edit_port = QLineEdit()
        self.edit_port.setPlaceholderText("22 / 80 / ssh")

        self.combo_proto = QComboBox()
        self.combo_proto.addItems([self.trans.get("fw_protocol_any"), self.trans.get("fw_protocol_tcp"), self.trans.get("fw_protocol_udp")])

        self.combo_action = QComboBox()
        self.combo_action.addItems([self.trans.get("fw_action_allow"), self.trans.get("fw_action_deny"), self.trans.get("fw_action_reject")])

        self.combo_dir = QComboBox()
        self.combo_dir.addItems([self.trans.get("fw_direction_in"), self.trans.get("fw_direction_out")])

        form.addRow(self.trans.get("fw_rule_port"), self.edit_port)
        form.addRow(self.trans.get("fw_rule_protocol"), self.combo_proto)
        form.addRow(self.trans.get("fw_rule_action"), self.combo_action)
        form.addRow(self.trans.get("fw_rule_direction"), self.combo_dir)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton(self.trans.get("close"))
        self.btn_ok = QPushButton(self.trans.get("fw_add_rule"))
        for b in [self.btn_cancel, self.btn_ok]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(40)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        root.addLayout(btn_row)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {c['bg']}; color: {c['text']}; }}
            QLineEdit {{
                background-color: {c['bg']}; color: {c['text']};
                border: 2px solid {c['card2']}; border-radius: 10px;
                padding: 10px 12px; min-height: 40px;
            }}
            QComboBox {{
                background-color: {c['bg']}; color: {c['text']};
                border: 2px solid {c['card2']}; border-radius: 10px;
                padding: 8px 12px; min-height: 40px;
            }}
            QPushButton {{
                background-color: {c['card2']}; color: {c['text']};
                border-radius: 10px; padding: 8px 14px;
            }}
            QPushButton:hover {{ border: 1px solid {c['accent']}; }}
        """)

    def values(self):
        port = self.edit_port.text().strip()
        proto_txt = self.combo_proto.currentText()
        action_txt = self.combo_action.currentText()
        dir_txt = self.combo_dir.currentText()

        proto_map = {
            self.trans.get("fw_protocol_any"): "any",
            self.trans.get("fw_protocol_tcp"): "tcp",
            self.trans.get("fw_protocol_udp"): "udp",
        }
        action_map = {
            self.trans.get("fw_action_allow"): "allow",
            self.trans.get("fw_action_deny"): "deny",
            self.trans.get("fw_action_reject"): "reject",
        }
        dir_map = {
            self.trans.get("fw_direction_in"): "in",
            self.trans.get("fw_direction_out"): "out",
        }
        return action_map.get(action_txt, "allow"), dir_map.get(dir_txt, "in"), port, proto_map.get(proto_txt, "any")

# ─── Main Firewall View ────────────────────────────────────────────────────────
class FirewallView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.is_dark = True
        self._backend = FirewallManagerBackend()
        self._toggle_thread = None
        self._profile_thread = None
        self._status_thread = None
        self._rules_thread = None
        self._delete_thread = None
        self._add_rule_thread = None
        self._log_thread = None
        self._install_thread = None
        self._fw_enabled = False
        self._last_status_ms = 0
        self._status_cache_ttl_ms = 30000  # Increased to 30 seconds to reduce polling
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(30000)  # 30 seconds instead of 8
        self._auto_refresh_timer.timeout.connect(self._refresh_status_cached)
        self._logging_ensured = False
        self._permission_denied = False
        self._unlock_btn = None
        self._init_ui()
        QTimer.singleShot(300, self._refresh_status)

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

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 36, 40, 24)
        outer.setSpacing(0)

        # — Title with Global Status —
        title_row = QHBoxLayout()
        
        # Status indicator on the left
        self.global_status_dot = QLabel()
        self.global_status_dot.setFixedSize(16, 16)
        self.global_status_dot.setStyleSheet("""
            QLabel { 
                background-color: #f38ba8; 
                border-radius: 8px; 
                border: 2px solid #45475a;
            }
        """)
        
        self.global_status_lbl = QLabel()
        self.global_status_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f38ba8;")
        
        status_col = QHBoxLayout()
        status_col.addWidget(self.global_status_dot)
        status_col.addWidget(self.global_status_lbl)
        status_col.addStretch()
        
        title_col = QVBoxLayout()
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa;")
        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #585b70;")
        title_col.addLayout(status_col)
        title_col.addWidget(self.title_lbl)
        title_col.addWidget(self.subtitle_lbl)
        title_row.addLayout(title_col)
        title_row.addStretch()

        # Mode pills
        self.mode_basic = ModePill()
        self.mode_advanced = ModePill()
        self.mode_basic.setChecked(True)
        self.mode_basic.clicked.connect(lambda: self._set_mode(0))
        self.mode_advanced.clicked.connect(lambda: self._set_mode(1))
        title_row.addWidget(self.mode_basic)
        title_row.addWidget(self.mode_advanced)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(40, 40)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton { background: #313244; color: #89b4fa; border-radius: 20px;
                font-size: 18px; border: none; }
            QPushButton:hover { background: #45475a; }
        """)
        self.refresh_btn.clicked.connect(self._refresh_status)
        title_row.addWidget(self.refresh_btn)
        outer.addLayout(title_row)
        outer.addSpacing(30)

        # — NOT INSTALLED warning —
        self.not_installed_frame = QFrame()
        self.not_installed_frame.setStyleSheet("""
            QFrame { background-color: #2e1a0a; border-radius: 14px; 
                     border: 2px solid #fab387; padding: 15px; }
        """)
        ni_layout = QVBoxLayout(self.not_installed_frame)
        ni_icon = QLabel("⚠️")
        ni_icon.setStyleSheet("font-size: 36px;")
        ni_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ni_layout.addWidget(ni_icon)
        self.not_installed_lbl = QLabel()
        self.not_installed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.not_installed_lbl.setStyleSheet("color: #fab387; font-size: 15px; font-weight: bold;")
        self.not_installed_lbl.setWordWrap(True)
        ni_layout.addWidget(self.not_installed_lbl)
        
        install_hint = QLabel("sudo apt install ufw")
        install_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        install_hint.setStyleSheet("""
            color: #cdd6f4; font-family: monospace; font-size: 14px; 
            background: #181825; border-radius: 6px; padding: 6px 14px;
        """)
        ni_layout.addWidget(install_hint)

        self.fix_btn = QPushButton()
        self.fix_btn.setMinimumHeight(45)
        self.fix_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fix_btn.setStyleSheet("""
            QPushButton { background-color: #fab387; color: #11111b; font-weight: bold; 
                         border-radius: 8px; font-size: 14px; border: none; margin-top: 10px; }
            QPushButton:hover { background-color: #89b4fa; }
        """)
        self.fix_btn.clicked.connect(self._on_fix_clicked)
        ni_layout.addWidget(self.fix_btn)

        self.not_installed_frame.hide()
        outer.addWidget(self.not_installed_frame)

        # — Dual-mode content (stack) —
        self.mode_stack = QStackedWidget()
        outer.addWidget(self.mode_stack)

        # ── Basic Protection page ──────────────────────────────────────────
        self.main_frame = QWidget()
        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setSpacing(28)

        # Master toggle card
        toggle_card = QFrame()
        toggle_card.setStyleSheet("QFrame { background-color: #1e1e2e; border-radius: 20px; padding: 8px; }")
        toggle_inner = QHBoxLayout(toggle_card)
        toggle_inner.setContentsMargins(30, 20, 30, 20)

        # Left: toggle button
        self.toggle_btn = MasterToggleButton()
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        toggle_inner.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        toggle_inner.addSpacing(30)

        # Right: status info
        status_col = QVBoxLayout()
        self.status_header = QLabel()
        self.status_header.setStyleSheet("font-size: 20px; font-weight: bold;")
        status_col.addWidget(self.status_header)

        dot_row = QHBoxLayout()
        self.pulse_dot = PulsingDot("#a6e3a1")
        dot_row.addWidget(self.pulse_dot)
        self.status_text = QLabel()
        self.status_text.setStyleSheet("font-size: 14px; color: #a6e3a1; font-weight: bold;")
        dot_row.addWidget(self.status_text)
        dot_row.addStretch()
        status_col.addLayout(dot_row)

        self.status_desc = QLabel()
        self.status_desc.setStyleSheet("font-size: 12px; color: #585b70;")
        self.status_desc.setWordWrap(True)
        status_col.addWidget(self.status_desc)
        status_col.addStretch()
        toggle_inner.addLayout(status_col, stretch=1)
        main_layout.addWidget(toggle_card)

        # Quick profiles section
        self.profiles_lbl = QLabel()
        self.profiles_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        main_layout.addWidget(self.profiles_lbl)

        profiles_row = QHBoxLayout()
        profiles_row.setSpacing(14)

        self._profile_group = QButtonGroup(self)
        self._profile_group.setExclusive(True)

        c = self._c
        self.btn_home = ProfileButton("home", "🏠", "", c)
        self.btn_public = ProfileButton("public", "🏢", "", c)
        self.btn_kill = ProfileButton("kill", "⛔", "", c)

        for btn in [self.btn_home, self.btn_public, self.btn_kill]:
            self._profile_group.addButton(btn)
            profiles_row.addWidget(btn)
            btn.clicked.connect(lambda checked, b=btn: self._on_profile_clicked(b.profile_name))

        self.btn_home.setChecked(True)
        self.btn_home._refresh_style(True)
        main_layout.addLayout(profiles_row)

        # Rules info label
        self.rules_lbl = QLabel()
        self.rules_lbl.setStyleSheet("font-size: 12px; color: #585b70; font-style: italic;")
        self.rules_lbl.setWordWrap(True)
        main_layout.addWidget(self.rules_lbl)

        main_layout.addStretch()
        self.mode_stack.addWidget(self.main_frame)  # index 0

        # ── Advanced Console page ──────────────────────────────────────────
        self.advanced_frame = QWidget()
        adv_layout = QVBoxLayout(self.advanced_frame)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.setSpacing(14)

        # Advanced toggles
        toggles_row = QHBoxLayout()
        self.chk_ipv6 = QCheckBox()
        self.chk_icmp = QCheckBox()
        self.chk_ipv6.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_icmp.setCursor(Qt.CursorShape.PointingHandCursor)
        toggles_row.addWidget(self.chk_ipv6)
        toggles_row.addWidget(self.chk_icmp)
        toggles_row.addStretch()
        adv_layout.addLayout(toggles_row)

        split = QSplitter(Qt.Orientation.Vertical)
        split.setChildrenCollapsible(False)

        # Rules table card
        rules_card = QFrame()
        rules_card.setObjectName("rulesCard")
        rcl = QVBoxLayout(rules_card)
        rcl.setContentsMargins(16, 14, 16, 14)
        rcl.setSpacing(10)

        rules_header = QHBoxLayout()
        self.rules_title = QLabel()
        self.rules_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        rules_header.addWidget(self.rules_title)
        rules_header.addStretch()
        
        # Add sync button
        self.btn_sync_rules = QPushButton()
        self.btn_sync_rules.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_rules.setMinimumHeight(36)
        self.btn_sync_rules.clicked.connect(self._sync_rules_clicked)
        rules_header.addWidget(self.btn_sync_rules)
        
        self.btn_add_rule = QPushButton()
        self.btn_add_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_rule.setMinimumHeight(40)
        self.btn_add_rule.clicked.connect(self._open_add_rule_dialog)
        rules_header.addWidget(self.btn_add_rule)
        rcl.addLayout(rules_header)

        # Update table to 8 columns for icons
        self.rules_table = QTableWidget(0, 8)
        self.rules_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rules_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rcl.addWidget(self.rules_table)

        split.addWidget(rules_card)

        # Logs card
        logs_card = QFrame()
        logs_card.setObjectName("logsCard")
        lcl = QVBoxLayout(logs_card)
        lcl.setContentsMargins(16, 14, 16, 14)
        lcl.setSpacing(10)

        logs_header = QHBoxLayout()
        self.logs_title = QLabel()
        self.logs_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        logs_header.addWidget(self.logs_title)
        logs_header.addStretch()
        self.btn_clear_logs = QPushButton("Clear")
        self.btn_clear_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_logs.setMinimumHeight(36)
        self.btn_clear_logs.clicked.connect(lambda: self.log_box.setPlainText(""))
        logs_header.addWidget(self.btn_clear_logs)
        lcl.addLayout(logs_header)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(2000)
        lcl.addWidget(self.log_box)

        # Empty-state overlay
        self.logs_empty = QFrame()
        self.logs_empty.setObjectName("logsEmpty")
        self.logs_empty.setStyleSheet("QFrame { background: transparent; }")
        empty_l = QVBoxLayout(self.logs_empty)
        empty_l.setContentsMargins(0, 0, 0, 0)
        empty_l.setSpacing(10)
        self.lbl_no_logs = QLabel()
        self.lbl_no_logs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_logs.setWordWrap(True)
        self.btn_enable_logging = QPushButton()
        self.btn_enable_logging.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enable_logging.setMinimumHeight(40)
        self.btn_enable_logging.clicked.connect(self._enable_logging_clicked)
        empty_l.addStretch()
        empty_l.addWidget(self.lbl_no_logs)
        empty_l.addWidget(self.btn_enable_logging, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_l.addStretch()
        lcl.addWidget(self.logs_empty)
        self.logs_empty.hide()

        split.addWidget(logs_card)
        split.setSizes([420, 260])
        adv_layout.addWidget(split)

        self.mode_stack.addWidget(self.advanced_frame)  # index 1

        self.retranslate()
        self._update_status_ui(False)
        self._set_mode(0)

    # ── Status refresh ────────────────────────────────────────────────────────
    def _refresh_status(self):
        self.refresh_btn.setEnabled(False)
        self.status_text.setText(self.trans.get("ufw_refreshing"))
        self.status_text.setStyleSheet("font-size: 14px; color: #fab387; font-weight: bold;")
        
        self._status_thread = StatusThread(self._backend, self)
        self._status_thread.status_ready.connect(self._on_status_ready)
        self._status_thread.start()

    def _refresh_status_cached(self):
        # Only refresh if explicitly requested or if cache expired
        now = int(QDateTime.currentMSecsSinceEpoch())
        if now - self._last_status_ms < self._status_cache_ttl_ms:
            return
        # Only auto-refresh in advanced mode to avoid constant prompts
        if self.mode_stack.currentIndex() == 1:
            self._refresh_status()

    def refresh_now(self):
        self._last_status_ms = 0
        self._permission_denied = False
        self._hide_unlock_button()
        self._refresh_status()
        if self.mode_stack.currentIndex() == 1:
            self._refresh_rules()

    def _on_fix_clicked(self):
        """Handle UFW installation in a separate thread to avoid UI blocking."""
        if self._install_thread and self._install_thread.isRunning():
            return
            
        self._install_thread = InstallUfwThread(self)
        self._install_thread.done.connect(self._on_install_done)
        self._install_thread.start()

    def _on_install_done(self, success: bool):
        if success:
            QMessageBox.information(self, "Installing UFW", "Terminal prompt opened to install UFW. Please refresh once complete.")
        else:
            QMessageBox.warning(self, "Error", "Could not launch installer. Please install UFW manually: sudo apt install ufw")

    def _on_status_ready(self, result: dict):
        self.refresh_btn.setEnabled(True)
        self._last_status_ms = int(QDateTime.currentMSecsSinceEpoch())
        
        # Check for permission denied
        if result.get("error") and "Permission denied" in result.get("error", ""):
            self._permission_denied = True
            self._show_unlock_button()
            return
            
        self._permission_denied = False
        self._hide_unlock_button()
        
        if not result["installed"]:
            self.not_installed_frame.show()
            self.main_frame.hide()
            self.advanced_frame.hide()
            self.not_installed_lbl.setText(
                self.trans.get("ufw_not_installed") or
                "UFW is not installed on this system.\nInstall it with:"
            )
            return

        self.not_installed_frame.hide()
        self.main_frame.show()
        self.advanced_frame.show()
        enabled = result["enabled"]
        self._fw_enabled = enabled
        self._update_status_ui(enabled)
        self.toggle_btn.set_enabled_state(enabled)

        rules = result.get("rules", [])
        if rules:
            self.rules_lbl.setText(self.trans.get("fw_rules") + ": " + "  |  ".join(rules[:4]))
        else:
            self.rules_lbl.setText("")

        if self.mode_stack.currentIndex() == 1:
            self._refresh_rules()

    def _update_status_ui(self, enabled: bool):
        c = self._c
        if enabled:
            # Update global status
            self.global_status_dot.setStyleSheet(f"""
                QLabel {{ 
                    background-color: {c['green']}; 
                    border-radius: 8px; 
                    border: 2px solid {c['card2']};
                }}
            """)
            self.global_status_lbl.setText(self.trans.get("fw_active") or "Firewall Active")
            self.global_status_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {c['green']};")
            
            self.status_header.setText(self.trans.get("fw_protected") or "System Protected")
            # Security Green
            self.status_header.setStyleSheet("font-size: 20px; font-weight: bold; color: #40a02b;")
            self.status_text.setText(self.trans.get("fw_active") or "Firewall Active")
            self.status_text.setStyleSheet("font-size: 14px; color: #40a02b; font-weight: bold;")
            self.status_desc.setText(
                self.trans.get("fw_protected_desc") or
                "Your system is protected. Incoming connections are filtered by UFW."
            )
            self.pulse_dot.set_color("#40a02b")
        else:
            # Update global status
            self.global_status_dot.setStyleSheet(f"""
                QLabel {{ 
                    background-color: {c['red']}; 
                    border-radius: 8px; 
                    border: 2px solid {c['card2']};
                }}
            """)
            self.global_status_lbl.setText(self.trans.get("fw_system_vulnerable") or "System Vulnerable")
            self.global_status_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {c['red']};")
            
            self.status_header.setText(self.trans.get("fw_unprotected") or "System Unprotected")
            # Warning Red
            self.status_header.setStyleSheet("font-size: 20px; font-weight: bold; color: #d20f39;")
            self.status_text.setText(self.trans.get("fw_inactive") or "Firewall Inactive")
            self.status_text.setStyleSheet("font-size: 14px; color: #d20f39; font-weight: bold;")
            self.status_desc.setText(
                self.trans.get("fw_unprotected_desc") or
                "No active firewall. Enable it to block unauthorized incoming connections."
            )
            self.pulse_dot.set_color("#d20f39")

    # ── Toggle ─────────────────────────────────────────────────────────────────
    def _on_toggle_clicked(self):
        if self._toggle_thread and self._toggle_thread.isRunning():
            return
        new_state = not self._fw_enabled
        self.toggle_btn.set_loading(True)
        self._toggle_thread = ToggleThread(self._backend, new_state, self)
        self._toggle_thread.done.connect(self._on_toggle_done)
        self._toggle_thread.start()

    def _on_toggle_done(self, result: dict):
        self.toggle_btn.set_loading(False)
        if result["success"]:
            QTimer.singleShot(500, self._refresh_status)
        else:
            # Check for permission denied
            if "Permission denied" in result.get("message", "") or "cancelled" in result.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), result["message"] or self.trans.get("fw_auth_failed_desc"))
            # Reset button state
            self.toggle_btn.set_enabled_state(self._fw_enabled)

    # ── Profile ────────────────────────────────────────────────────────────────
    def _on_profile_clicked(self, profile_name: str):
        if self._profile_thread and self._profile_thread.isRunning():
            return

        self._profile_thread = ProfileThread(self._backend, profile_name, self)
        self._profile_thread.done.connect(lambda r: self._on_profile_done(r, profile_name))
        self._profile_thread.start()

    def _on_profile_done(self, result: dict, profile_name: str):
        if result["success"]:
            QTimer.singleShot(800, self._refresh_status)
            # Auto-sync rules in advanced mode
            if self.mode_stack.currentIndex() == 1:
                QTimer.singleShot(1200, self._refresh_rules)
        else:
            # Check for permission denied
            if "Permission denied" in result.get("message", "") or "cancelled" in result.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), result["message"])

    # ── Advanced: rules + logs ───────────────────────────────────────────────
    def _refresh_rules(self):
        if self._rules_thread and self._rules_thread.isRunning():
            return
        self._rules_thread = RulesThread(self._backend, self)
        self._rules_thread.done.connect(self._on_rules_ready)
        self._rules_thread.start()

    def _on_rules_ready(self, result: dict):
        if not result.get("success"):
            # Check for permission denied
            if "Permission denied" in result.get("message", "") or "cancelled" in result.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), result.get("message") or self.trans.get("fw_auth_failed_desc"))
            return
        rules = result.get("rules", [])
        self._populate_rules_table(rules)

    def _populate_rules_table(self, rules: list[dict]):
        self.rules_table.setRowCount(len(rules))
        for row, r in enumerate(rules):
            # Column 0: Status Icon
            action = str(r.get("action", "")).lower()
            if action == "allow":
                icon_label = QLabel("🟢")
                icon_label.setStyleSheet("font-size: 16px;")
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif action in ["deny", "reject"]:
                icon_label = QLabel("🔴")
                icon_label.setStyleSheet("font-size: 16px;")
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                icon_label = QLabel("⚪")
                icon_label.setStyleSheet("font-size: 16px;")
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rules_table.setCellWidget(row, 0, icon_label)
            
            # Column 1: ID
            self.rules_table.setItem(row, 1, QTableWidgetItem(str(r.get("id", ""))))
            # Column 2: Action
            self.rules_table.setItem(row, 2, QTableWidgetItem(str(r.get("action", ""))))
            # Column 3: Direction
            self.rules_table.setItem(row, 3, QTableWidgetItem(str(r.get("direction", ""))))
            # Column 4: Port/Service
            self.rules_table.setItem(row, 4, QTableWidgetItem(str(r.get("port_service", ""))))
            # Column 5: Protocol
            self.rules_table.setItem(row, 5, QTableWidgetItem(str(r.get("protocol", ""))))
            # Column 6: Target
            self.rules_table.setItem(row, 6, QTableWidgetItem(str(r.get("target", ""))))
            # Column 7: Delete button
            btn = QPushButton(self.trans.get("fw_rule_delete"))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(30)
            rule_id = int(r.get("id", 0) or 0)
            btn.clicked.connect(lambda _=False, rid=rule_id: self._delete_rule(rid))
            self.rules_table.setCellWidget(row, 7, btn)

    def _sync_rules_clicked(self):
        """Handle sync rules button click."""
        self._refresh_rules()

    def _delete_rule(self, rule_id: int):
        if rule_id <= 0:
            return
        if self._delete_thread and self._delete_thread.isRunning():
            return
        self._delete_thread = DeleteRuleThread(self._backend, rule_id, self)
        self._delete_thread.done.connect(self._on_delete_done)
        self._delete_thread.start()

    def _on_delete_done(self, result: dict):
        if result.get("success"):
            QTimer.singleShot(350, self._refresh_status)
        else:
            # Check for permission denied
            if "Permission denied" in result.get("message", "") or "cancelled" in result.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), result.get("message") or self.trans.get("fw_auth_failed_desc"))

    def _open_add_rule_dialog(self):
        dlg = AddRuleDialog(self.trans, self._c, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        action, direction, port, proto = dlg.values()
        if not port:
            return
        if self._add_rule_thread and self._add_rule_thread.isRunning():
            return
        self._add_rule_thread = AddRuleThread(self._backend, action, direction, port, proto, self)
        self._add_rule_thread.done.connect(self._on_add_rule_done)
        self._add_rule_thread.start()

    def _on_add_rule_done(self, result: dict):
        if result.get("success"):
            QTimer.singleShot(450, self._refresh_status)
        else:
            # Check for permission denied
            if "Permission denied" in result.get("message", "") or "cancelled" in result.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), result.get("message") or self.trans.get("fw_auth_failed_desc"))

    def _start_log_thread(self):
        if self._log_thread and self._log_thread.isRunning():
            return
        # Ensure logging is enabled once per app run (best-effort).
        if not self._logging_ensured:
            self._logging_ensured = True
            try:
                self._backend.ensure_logging_enabled()
            except Exception:
                pass

        self._log_thread = LogTailThread(parent=self)
        self._log_thread.line_ready.connect(self._append_log_line)
        self._log_thread.error.connect(self._on_log_error)
        self._log_thread.start()
        # show empty-state if nothing comes in quickly
        QTimer.singleShot(1200, self._evaluate_log_empty_state)

    def _stop_log_thread(self):
        if self._log_thread and self._log_thread.isRunning():
            self._log_thread.stop()
            self._log_thread.wait(800)
        self._log_thread = None

    def _append_log_line(self, line: str):
        if self.logs_empty.isVisible():
            self.logs_empty.hide()
        
        # Apply highlighting based on log content
        formatted_line = line
        if "[UFW BLOCK]" in line.upper():
            # Dark red for blocked traffic
            formatted_line = f'<span style="color: #dc143c; font-weight: bold;">{line}</span>'
        elif "[UFW ALLOW]" in line.upper():
            # Dark green for allowed traffic  
            formatted_line = f'<span style="color: #006400; font-weight: bold;">{line}</span>'
        
        # Use appendHtml for colored text
        cursor = self.log_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(formatted_line + "<br>")
        self.log_box.setTextCursor(cursor)
        self.log_box.ensureCursorVisible()
        
        # Memory optimization: keep only last 200 lines
        if self.log_box.document().blockCount() > 200:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 20)
            cursor.removeSelectedText()

    def _on_log_error(self, code: str):
        if code == "permission":
            self._permission_denied = True
            self._show_unlock_button()
        else:
            self._show_logs_empty_state()

    def _evaluate_log_empty_state(self):
        if self.mode_stack.currentIndex() != 1:
            return
        if self.log_box.document().blockCount() <= 1:
            self._show_logs_empty_state()

    def _show_logs_empty_state(self):
        self.logs_empty.show()

    def _enable_logging_clicked(self):
        res = self._backend.enable_logging(True)
        if not res.get("success"):
            # Check for permission denied
            if "Permission denied" in res.get("message", "") or "cancelled" in res.get("message", "").lower():
                self._permission_denied = True
                self._show_unlock_button()
            else:
                QMessageBox.warning(self, self.trans.get("fw_auth_failed"), res.get("message") or self.trans.get("fw_auth_failed_desc"))
            return
        self.logs_empty.hide()
        self.log_box.appendPlainText("[ufw] logging enabled.")
        self._stop_log_thread()
        self._start_log_thread()

    # ── Unlock Button for Permission Denied ───────────────────────────────────
    def _show_unlock_button(self):
        """Show unlock button when permission is denied."""
        if self._unlock_btn is None:
            self._unlock_btn = QPushButton("🔓 Unlock")
            self._unlock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._unlock_btn.setMinimumHeight(40)
            self._unlock_btn.clicked.connect(self._on_unlock_clicked)
            # Add to the status area
            status_col = self.toggle_btn.parent().layout().itemAt(1).layout()
            if status_col:
                status_col.insertWidget(3, self._unlock_btn)
        
        self._unlock_btn.show()
        self.status_header.setText("Authentication Required")
        self.status_header.setStyleSheet("font-size: 20px; font-weight: bold; color: #fab387;")
        self.status_text.setText("Click Unlock to authenticate")
        self.status_text.setStyleSheet("font-size: 14px; color: #fab387; font-weight: bold;")

    def _hide_unlock_button(self):
        """Hide unlock button when permission is restored."""
        if self._unlock_btn:
            self._unlock_btn.hide()

    def _on_unlock_clicked(self):
        """Handle unlock button click - trigger authentication."""
        self._permission_denied = False
        self._hide_unlock_button()
        self.refresh_now()

    # ── Theme ──────────────────────────────────────────────────────────────────
    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = self._c
        self.setStyleSheet(f"background-color: {c['bg']};")
        self.title_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {c['accent']};")
        self.subtitle_lbl.setStyleSheet(f"font-size: 13px; color: {c['muted']};")
        self.profiles_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {c['text']};")
        self.rules_lbl.setStyleSheet(f"font-size: 12px; color: {c['muted']}; font-style: italic;")
        self.main_frame.setStyleSheet(f"background: {c['bg']};")

        self.mode_basic.apply_style(c)
        self.mode_advanced.apply_style(c)

        for btn in [self.btn_home, self.btn_public, self.btn_kill]:
            btn.set_theme(c)

        self.advanced_frame.setStyleSheet(f"background: {c['bg']};")
        self.rules_table.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']}; gridline-color: {c['card2']};")
        self.log_box.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']}; border: 2px solid {c['card2']}; border-radius: 12px; padding: 10px; font-family: monospace;")
        self.lbl_no_logs.setStyleSheet(f"color: {c['muted']}; font-size: 13px; font-weight: bold;")
        self.btn_enable_logging.setStyleSheet(f"background-color: {c['accent']}; color: #11111b; border-radius: 10px; padding: 8px 14px; font-weight: bold;")
        self.chk_ipv6.setStyleSheet(f"color: {c['text']}; font-weight: bold;")
        self.chk_icmp.setStyleSheet(f"color: {c['text']}; font-weight: bold;")
        self.btn_add_rule.setStyleSheet(f"background-color: {c['accent']}; color: #11111b; border-radius: 10px; padding: 8px 14px; font-weight: bold;")
        self.btn_clear_logs.setStyleSheet(f"background-color: {c['card2']}; color: {c['text']}; border-radius: 10px; padding: 6px 12px;")
        # Cards already styled via their children; keep container neutral.

        self._update_status_ui(self._fw_enabled)

    def retranslate(self):
        self.title_lbl.setText(self.trans.get("firewall_manager") or "Firewall Manager")
        self.subtitle_lbl.setText(
            self.trans.get("firewall_subtitle") or
            "Control your UFW firewall — enable, disable, and set security profiles"
        )
        self.mode_basic.setText(self.trans.get("fw_mode_basic"))
        self.mode_advanced.setText(self.trans.get("fw_mode_advanced"))
        self.profiles_lbl.setText(self.trans.get("fw_profiles_quick"))
        self.not_installed_lbl.setText(
            self.trans.get("ufw_not_installed") or
            "UFW is not installed on this system.\nInstall it with:"
        )
        self.fix_btn.setText(self.trans.get("ufw_fix_btn") or "🛠 Fix (Install UFW)")

        # Profile button texts
        self.btn_home._name = self.trans.get("fw_profile_home")
        self.btn_home._desc = self.trans.get("fw_profile_home_desc")
        self.btn_home._refresh_style(self.btn_home.isChecked())

        self.btn_public._name = self.trans.get("fw_profile_public")
        self.btn_public._desc = self.trans.get("fw_profile_public_desc")
        self.btn_public._refresh_style(self.btn_public.isChecked())

        self.btn_kill._name = self.trans.get("fw_profile_kill")
        self.btn_kill._desc = self.trans.get("fw_profile_kill_desc")
        self.btn_kill._refresh_style(self.btn_kill.isChecked())

        # Advanced labels
        self.chk_ipv6.setText(self.trans.get("fw_ipv6"))
        self.chk_icmp.setText(self.trans.get("fw_icmp_hide"))
        self.rules_title.setText(self.trans.get("fw_active_rules"))
        self.logs_title.setText(self.trans.get("fw_telemetry"))
        self.btn_sync_rules.setText(self.trans.get("fw_sync_rules"))
        self.btn_add_rule.setText(self.trans.get("fw_add_rule"))
        self.lbl_no_logs.setText(self.trans.get("fw_no_logs"))
        self.btn_enable_logging.setText(self.trans.get("fw_enable_logging"))

        self.rules_table.setHorizontalHeaderLabels([
            "",
            "ID",
            self.trans.get("fw_rule_action"),
            self.trans.get("fw_rule_direction"),
            self.trans.get("fw_rule_port"),
            self.trans.get("fw_rule_protocol"),
            "Target",
            self.trans.get("fw_rule_delete"),
        ])

    def _set_mode(self, idx: int):
        self.mode_stack.setCurrentIndex(idx)
        self.mode_basic.blockSignals(True)
        self.mode_advanced.blockSignals(True)
        self.mode_basic.setChecked(idx == 0)
        self.mode_advanced.setChecked(idx == 1)
        self.mode_basic.blockSignals(False)
        self.mode_advanced.blockSignals(False)

        if idx == 1:
            self._refresh_rules()
            self._start_log_thread()
            if not self._auto_refresh_timer.isActive():
                self._auto_refresh_timer.start()
        else:
            self._stop_log_thread()
            self._auto_refresh_timer.stop()
