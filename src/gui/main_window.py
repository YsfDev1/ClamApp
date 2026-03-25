from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget,
                             QProgressBar, QMessageBox, QFileDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox, QDialog, QTextEdit,
                             QTabWidget, QSplitter, QSizePolicy, QPlainTextEdit,
                             QProgressDialog, QScrollArea, QLineEdit, QTimeEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime, QUrl
from PyQt6.QtGui import QFont, QIcon, QColor, QDragEnterEvent, QDropEvent, QPalette, QDesktopServices
import os
import sys
import stat


# ─────────────────────────────────────────────────────────
#  DB Update Thread — runs freshclam off the GUI thread
# ─────────────────────────────────────────────────────────
class DbUpdateThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, wrapper, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper

    def run(self):
        try:
            result = self.wrapper.update_database()
            self.finished.emit(result)
        except Exception as exc:
            self.finished.emit({"status": "error", "message": str(exc)})


if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.clam_wrapper import ClamWrapper
from backend.data_manager import DataManager
from gui.scanner_thread import ScannerThread
from gui.translations import Translations
from gui.password_gen_view import PasswordGeneratorView
from gui.cipher_view import CipherView
from gui.hash_tool_view import HashToolView
from gui.network_view import NetworkView
from gui.shredder_view import ShredderView
from gui.vault_view import VaultView
from gui.privacy_view import PrivacyView
from gui.cloud_scan_view import CloudScanView
from gui.breach_checker_view import BreachCheckerView
from gui.firewall_view import FirewallView

from modules.usb_guardian import USBGuardianLogic
from backend.config_manager import SettingsManager
from modules.scheduler_logic import ScheduleLogic
from gui.schedule_view import ScheduleView

# ─────────────────────────────────────────────────────────
#  Theming helper
# ─────────────────────────────────────────────────────────
DARK = {
    "bg": "#181825", "sidebar": "#1e1e2e", "sidebar_border": "#313244",
    "card": "#313244", "card2": "#45475a", "text": "#cdd6f4",
    "subtext": "#bac2de", "muted": "#585b70", "accent": "#89b4fa",
    "green": "#a6e3a1", "red": "#f38ba8", "orange": "#fab387",
    "btn_hover": "#313244", "btn_checked": "#45475a",
}
LIGHT = {
    "bg": "#eff1f5", "sidebar": "#dce0e8", "sidebar_border": "#ccd0da",
    "card": "#e6e9ef", "card2": "#ccd0da", "text": "#4c4f69",
    "subtext": "#6c6f85", "muted": "#9ca0b0", "accent": "#1e66f5",
    "green": "#40a02b", "red": "#d20f39", "orange": "#fe640b",
    "btn_hover": "#ccd0da", "btn_checked": "#bcc0cc",
}


def apply_palette(widget, c):
    pal = widget.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(c["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(c["card"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(c["card2"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
    widget.setPalette(pal)
    widget.setAutoFillBackground(True)


# ─────────────────────────────────────────────────────────
#  Code Viewer Dialog
# ─────────────────────────────────────────────────────────
class CodeViewerDialog(QDialog):
    def __init__(self, title, content, translations, is_binary=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        
        layout = QVBoxLayout(self)
        
        if is_binary:
            warn = QLabel(f"⚠ {translations.get('binary_file_detected')}")
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #fab387; font-weight: bold; margin-bottom: 5px;")
            layout.addWidget(warn)
        else:
            warn = QLabel(translations.get("safe_viewer_warn"))
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #f38ba8; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(warn)
            
        self.te = QPlainTextEdit()
        self.te.setReadOnly(True)
        self.te.setPlainText(content)
        self.te.setStyleSheet("background-color: #181825; border: 1px solid #45475a; font-family: 'Courier New', monospace; font-size: 13px;")
        layout.addWidget(self.te)
        
        btn_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton(translations.get("copy"))
        self.btn_copy.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(self.btn_copy)
        
        btn_close = QPushButton(translations.get("close"))
        btn_close.setStyleSheet("background-color: #45475a; color: #cdd6f4; padding: 10px; border-radius: 5px;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def _copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.te.toPlainText())
        self.btn_copy.setText(f"✓ {self.btn_copy.text()}")
        QTimer.singleShot(2000, lambda: self.btn_copy.setText(self.btn_copy.text().replace("✓ ", "")))


# ─────────────────────────────────────────────────────────
#  Modern Sidebar
# ─────────────────────────────────────────────────────────
class ModernSidebar(QFrame):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.is_dark = True
        self.setFixedWidth(200)
        self._setup()

    def _btn_style(self, c):
        return f"""
            QPushButton {{ background-color: transparent; color: #bac2de; border: none; 
                          border-radius: 8px; padding: 12px; text-align: left; font-size: 14px; }}
            QPushButton:hover {{ background-color: #313244; color: #89b4fa; }}
            QPushButton:checked {{ background-color: #313244; color: #89b4fa; font-weight: bold; border-left: 4px solid #89b4fa; }}
        """

    def _setup(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)

        self.logo = QLabel("ClamApp")
        self.logo.setStyleSheet("color: #89b4fa; font-size: 24px; font-weight: bold; margin-bottom: 20px; padding-left: 15px;")
        layout.addWidget(self.logo)

        self.btn_dashboard = QPushButton(f"🏠 {self.trans.get('dashboard')}")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)

        self.btn_scan = QPushButton(f"🔍 {self.trans.get('scan')}")
        self.btn_scan.setCheckable(True)

        self.btn_quarantine = QPushButton(f"🛡 {self.trans.get('quarantine')}")
        self.btn_quarantine.setCheckable(True)

        self.btn_schedule = QPushButton(f"📅 {self.trans.get('schedule')}")
        self.btn_schedule.setCheckable(True)

        # Separator label
        self.sep_label = QLabel()
        self.sep_label.setFixedHeight(1)
        self.sep_label.setStyleSheet("background-color: #313244; margin: 4px 10px;")

        self.btn_network = QPushButton(f"🌐 {self.trans.get('active_connections')}")
        self.btn_network.setCheckable(True)

        self.btn_cloud = QPushButton(f"☁ {self.trans.get('cloud_scan')}")
        self.btn_cloud.setCheckable(True)

        self.btn_security = QPushButton(f"🔒 {self.trans.get('security_tools')}")
        self.btn_security.setCheckable(True)

        self.btn_audit = QPushButton(f"📋 {self.trans.get('security_audit')}")
        self.btn_audit.setCheckable(True)
        self.btn_audit.hide() # Disabled for v1.0 focus

        self.btn_breach = QPushButton(f"🔍 {self.trans.get('breach_checker')}")
        self.btn_breach.setCheckable(True)

        self.btn_firewall = QPushButton(f"🔥 {self.trans.get('firewall_manager')}")
        self.btn_firewall.setCheckable(True)

        self.btn_settings = QPushButton(f"⚙ {self.trans.get('settings')}")
        self.btn_settings.setCheckable(True)

        for btn in [self.btn_dashboard, self.btn_scan, self.btn_quarantine, self.btn_schedule]:
            layout.addWidget(btn)
        layout.addWidget(self.sep_label)
        for btn in [self.btn_network, self.btn_cloud, self.btn_security,
                    self.btn_audit, self.btn_breach, self.btn_firewall]:
            layout.addWidget(btn)
        layout.addStretch()
        layout.addWidget(self.btn_settings)

        self.version_label = QLabel(f"v1.0.0-{self.trans.get('stable')}")
        self.version_label.setStyleSheet("color: #585b70; padding: 10px;")
        layout.addWidget(self.version_label)
        self.apply_theme(self.is_dark)

    @property
    def _all_nav_btns(self):
        return [self.btn_dashboard, self.btn_scan, self.btn_quarantine, self.btn_schedule,
                self.btn_network, self.btn_cloud, self.btn_security,
                self.btn_audit, self.btn_breach, self.btn_firewall, self.btn_settings]

    def apply_theme(self, dark=True):
        c = DARK if dark else LIGHT
        self.setStyleSheet(f"""
            ModernSidebar {{ background-color: {c['sidebar']}; border-right: 1px solid {c['sidebar_border']}; }}
        """)
        for btn in self._all_nav_btns:
            btn.setStyleSheet(self._btn_style(c))
        self.logo.setStyleSheet(f"color: {c['accent']}; font-size: 24px; font-weight: bold; margin-bottom: 20px; padding-left: 15px;")
        self.version_label.setStyleSheet(f"color: {c['muted']}; padding: 10px;")
        self.sep_label.setStyleSheet(f"background-color: {c['sidebar_border']}; margin: 4px 10px;")

    def retranslate(self):
        self.btn_dashboard.setText(f"🏠 {self.trans.get('dashboard')}")
        self.btn_scan.setText(f"🔍 {self.trans.get('scan')}")
        self.btn_quarantine.setText(f"🛡 {self.trans.get('quarantine')}")
        self.btn_schedule.setText(f"📅 {self.trans.get('schedule')}")
        self.btn_network.setText(f"🌐 {self.trans.get('active_connections')}")
        self.btn_cloud.setText(f"☁ {self.trans.get('cloud_scan')}")
        self.btn_security.setText(f"🔒 {self.trans.get('security_tools')}")
        self.btn_audit.setText(f"📋 {self.trans.get('security_audit')}")
        self.btn_breach.setText(f"🔍 {self.trans.get('breach_checker')}")
        self.btn_firewall.setText(f"🔥 {self.trans.get('firewall_manager')}")
        self.btn_settings.setText(f"⚙ {self.trans.get('settings')}")


# ─────────────────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────────────────
class DashboardView(QWidget):
    def __init__(self, wrapper, trans, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.is_dark = True
        layout = QVBoxLayout(self)

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #89b4fa; font-size: 32px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Dashboard Status Badge
        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setContentsMargins(10, 5, 10, 5)
        self.status_badge.setStyleSheet("border-radius: 12px; font-weight: bold; padding: 5px 15px;")
        layout.insertWidget(1, self.status_badge) # Below title

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

        self.status_card = QFrame()
        self.status_card.setStyleSheet("background-color: #313244; border-radius: 15px; padding: 20px;")
        card_layout = QVBoxLayout(self.status_card)

        self.status_title = QLabel()
        self.status_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        card_layout.addWidget(self.status_title)

        self.status_desc = QLabel()
        self.status_desc.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        card_layout.addWidget(self.status_desc)

        self.db_label = QLabel()
        self.db_label.setStyleSheet("color: #bac2de; font-size: 12px; margin-top: 10px;")
        card_layout.addWidget(self.db_label)

        layout.addWidget(self.status_card)
        self.stats_layout = QHBoxLayout()
        layout.addLayout(self.stats_layout)
        self.retranslate()
        layout.addStretch()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        apply_palette(self, c)
        self.time_label.setStyleSheet(f"color: {c['accent']}; font-size: 32px; font-weight: bold;")
        self.status_card.setStyleSheet(f"background-color: {c['card']}; border-radius: 15px; padding: 20px;")
        self.status_desc.setStyleSheet(f"color: {c['text']}; font-size: 14px;")
        self.db_label.setStyleSheet(f"color: {c['subtext']}; font-size: 12px;")
        
        # Update Dashboard Status Badge
        # Logic: If firewall is off OR clamscan not found -> Warning
        parent = self.window()
        is_secure = True
        if hasattr(parent, "firewall_view"):
            if not parent.firewall_view._fw_enabled:
                is_secure = False
        
        if is_secure:
            self.status_badge.setText(self.trans.get("system_status_secure"))
            self.status_badge.setStyleSheet(f"background-color: #40a02b; color: #11111b; border-radius: 12px; font-weight: bold; padding: 5px;")
        else:
            self.status_badge.setText(self.trans.get("system_status_warn"))
            self.status_badge.setStyleSheet(f"background-color: #d20f39; color: #11111b; border-radius: 12px; font-weight: bold; padding: 5px;")

        self.refresh_stats()

    def retranslate(self):
        is_ok = self.wrapper.is_installed()
        c = DARK if self.is_dark else LIGHT
        color = c["green"] if is_ok else c["red"]
        self.status_title.setText(self.trans.get("protected") if is_ok else self.trans.get("warning"))
        self.status_title.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        self.status_desc.setText(f"{self.trans.get('version')}: {self.wrapper.get_version()}")
        self.db_label.setText(f"{self.trans.get('last_update')}: {self.wrapper.get_database_info()}")
        self.refresh_stats()

    def refresh_stats(self):
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        c = DARK if self.is_dark else LIGHT
        stats = self.wrapper.data_manager.data["stats"]
        for key in ["total_scans", "threats_found", "objects_scanned"]:
            self.stats_layout.addWidget(self._stat_card(self.trans.get(key), str(stats[key]), c))

    def _stat_card(self, title, value, c):
        card = QFrame()
        card.setStyleSheet(f"background-color: {c['bg']}; border-radius: 10px; padding: 15px;")
        l = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet(f"color: {c['accent']}; font-size: 12px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {c['text']}; font-size: 18px; font-weight: bold;")
        l.addWidget(t)
        l.addWidget(v)
        return card

    def _update_time(self):
        self.time_label.setText(QDateTime.currentDateTime().toString("HH:mm:ss"))


# ─────────────────────────────────────────────────────────
#  Scrollable Unified Dashboard
# ─────────────────────────────────────────────────────────
class ScrollableDashboardView(QScrollArea):
    def __init__(self, wrapper, trans, data_manager, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        
        self.dashboard = DashboardView(wrapper, trans)
        
        layout.addWidget(self.dashboard)
        layout.addStretch()
        
        self.setWidget(container)

    def apply_theme(self, dark=True):
        self.dashboard.apply_theme(dark)
        c = DARK if dark else LIGHT
        self.setStyleSheet(f"background-color: {c['bg']}; border: none;")
        self.widget().setStyleSheet(f"background-color: {c['bg']};")


# ─────────────────────────────────────────────────────────
#  Scan View
# ─────────────────────────────────────────────────────────
class ScanView(QWidget):
    def __init__(self, wrapper, trans, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.is_dark = True
        layout = QVBoxLayout(self)
        self.setAcceptDrops(True)

        self.title = QLabel()
        self.title.setStyleSheet("color: #cdd6f4; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.title)

        self.hint = QLabel()
        self.hint.setStyleSheet("color: #585b70; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.hint)

        self.options_widget = QWidget()
        scan_options = QHBoxLayout(self.options_widget)

        self.btn_quick = QPushButton()
        self.btn_full = QPushButton()
        self.btn_custom = QPushButton()

        for btn in [self.btn_quick, self.btn_full, self.btn_custom]:
            btn.setStyleSheet("""
                QPushButton { background-color: #313244; color: #cdd6f4; border-radius: 10px;
                    padding: 30px; font-size: 16px; min-width: 150px; }
                QPushButton:hover { background-color: #45475a; border: 1px solid #89b4fa; }
            """)
            scan_options.addWidget(btn)
        layout.addWidget(self.options_widget)

        self.progress_frame = QFrame()
        self.progress_frame.setHidden(True)
        self.progress_frame.setStyleSheet("background-color: #313244; border-radius: 15px; padding: 20px;")
        progress_layout = QVBoxLayout(self.progress_frame)

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #45475a; border-radius: 10px; text-align: center; color: #cdd6f4; font-weight: bold; background-color: #1e1e2e; height: 25px; }
            QProgressBar::chunk { background-color: #89b4fa; border-radius: 8px; }
        """)
        self.progress_bar.setRange(0, 0)
        progress_layout.addWidget(self.progress_bar)

        self.btn_stop = QPushButton()
        self.btn_stop.setStyleSheet("background-color: #f38ba8; color: #1e1e2e; font-weight: bold; border-radius: 5px; padding: 10px;")
        progress_layout.addWidget(self.btn_stop)
        layout.addWidget(self.progress_frame)

        self.history_title = QLabel()
        self.history_title.setStyleSheet("color: #cdd6f4; font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(self.history_title)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_table)
        self.retranslate()
        layout.addStretch()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        apply_palette(self, c)
        self.title.setStyleSheet(f"color: {c['text']}; font-size: 24px; font-weight: bold;")
        self.hint.setStyleSheet(f"color: {c['muted']}; font-style: italic;")
        self.history_title.setStyleSheet(f"color: {c['text']}; font-size: 18px; font-weight: bold;")
        self.history_table.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']}; gridline-color: {c['card2']};")
        self.progress_frame.setStyleSheet(f"background-color: {c['card']}; border-radius: 15px; padding: 20px;")
        self.progress_label.setStyleSheet(f"color: {c['text']}; font-size: 16px;")
        for btn in [self.btn_quick, self.btn_full, self.btn_custom]:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {c['card']}; color: {c['text']}; border-radius: 10px;
                    padding: 30px; font-size: 16px; min-width: 150px; }}
                QPushButton:hover {{ background-color: {c['card2']}; border: 1px solid {c['accent']}; }}
            """)

    def retranslate(self):
        self.title.setText(self.trans.get("scan_title"))
        self.hint.setText(self.trans.get("drag_drop_hint"))
        self.btn_quick.setText(self.trans.get("quick_scan"))
        self.btn_full.setText(self.trans.get("full_scan"))
        self.btn_custom.setText(self.trans.get("custom_scan"))
        self.btn_stop.setText(self.trans.get("stop_scan"))
        self.history_title.setText(self.trans.get("history"))
        self.history_table.setHorizontalHeaderLabels([
            self.trans.get("date"), self.trans.get("type"),
            self.trans.get("threats"), self.trans.get("path")
        ])
        self.refresh_history()

    def refresh_history(self):
        history = self.wrapper.data_manager.data.get("scan_history", [])
        self.history_table.setRowCount(len(history))
        for i, e in enumerate(history):
            for j, k in enumerate(["date", "type", "threats", "path"]):
                self.history_table.setItem(i, j, QTableWidgetItem(str(e[k])))


# ─────────────────────────────────────────────────────────
#  Results Summary
# ─────────────────────────────────────────────────────────
class ResultsSummaryView(QWidget):
    def __init__(self, wrapper, trans, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.is_dark = True
        layout = QVBoxLayout(self)

        self.title = QLabel()
        self.title.setStyleSheet("color: #f38ba8; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.title)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        layout.addWidget(self.summary_label)

        self.list_widget = QTableWidget(0, 4)
        self.list_widget.setStyleSheet("background-color: #313244; color: #cdd6f4;")
        self.list_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.list_widget)

        self.btn_action = QPushButton()
        self.btn_action.setStyleSheet("background-color: #fab387; padding: 15px; font-weight: bold; border-radius: 5px;")
        layout.addWidget(self.btn_action)

        self.btn_back = QPushButton()
        self.btn_back.setStyleSheet("color: #bac2de; padding: 10px;")
        layout.addWidget(self.btn_back)
        self.retranslate()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        apply_palette(self, c)
        self.list_widget.setStyleSheet(f"background-color: {c['card']}; color: {c['text']}; gridline-color: {c['card2']};")
        self.btn_back.setStyleSheet(f"color: {c['subtext']}; padding: 10px;")
        self.summary_label.setStyleSheet(f"color: {c['text']}; font-size: 16px;")

    def retranslate(self):
        self.title.setText(self.trans.get("results_title"))
        self.btn_action.setText(self.trans.get("quarantine_all"))
        self.btn_back.setText(self.trans.get("back"))
        self.list_widget.setHorizontalHeaderLabels([
            self.trans.get("path"), "Status",
            self.trans.get("virus_type"), self.trans.get("fpp_label")
        ])

    def show_results(self, infected_files, raw_output=""):
        self.list_widget.setRowCount(len(infected_files))
        threat_map = {}
        for line in raw_output.splitlines():
            if "FOUND" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    threat_map[parts[0].strip()] = parts[1].replace("FOUND", "").strip()

        for i, f in enumerate(infected_files):
            threat_name = threat_map.get(f, "Unknown")
            description = self.wrapper.get_virus_description(threat_name)
            fpp = self.wrapper.calculate_fpp(f)
            self.list_widget.setItem(i, 0, QTableWidgetItem(f))
            self.list_widget.setItem(i, 1, QTableWidgetItem("FOUND"))
            self.list_widget.setItem(i, 2, QTableWidgetItem(description))
            fpp_item = QTableWidgetItem(f"{fpp}%")
            color = "#a6e3a1" if fpp > 60 else ("#f38ba8" if fpp < 30 else "#fab387")
            fpp_item.setForeground(QColor(color))
            self.list_widget.setItem(i, 3, fpp_item)

        if not infected_files:
            self.btn_action.setHidden(True)
            self.title.setText("Scan Clean")
            self.title.setStyleSheet("color: #a6e3a1; font-size: 24px; font-weight: bold;")
            self.summary_label.setText("No threats found.")
        else:
            self.btn_action.setHidden(False)
            self.title.setText(self.trans.get("results_title"))
            self.title.setStyleSheet("color: #f38ba8; font-size: 24px; font-weight: bold;")
            self.summary_label.setText(f"Found {len(infected_files)} potential threats.")


# ─────────────────────────────────────────────────────────
#  Quarantine View
# ─────────────────────────────────────────────────────────
class QuarantineView(QWidget):
    def __init__(self, wrapper, trans, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.is_dark = True
        layout = QVBoxLayout(self)
        self.qtitle = QLabel(self.trans.get("quarantine"))
        self.qtitle.setStyleSheet("color: #cdd6f4; font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.qtitle)
        self.table = QTableWidget(0, 3)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #313244; color: #cdd6f4;")
        layout.addWidget(self.table)
        self.retranslate()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        apply_palette(self, c)
        self.qtitle.setStyleSheet(f"color: {c['text']}; font-size: 24px; font-weight: bold;")
        self.table.setStyleSheet(f"background-color: {c['card']}; color: {c['text']}; gridline-color: {c['card2']};")

    def retranslate(self):
        self.qtitle.setText(self.trans.get("quarantine"))
        self.table.setHorizontalHeaderLabels([
            self.trans.get("original_path"), self.trans.get("date"), self.trans.get("actions")
        ])
        self.refresh()

    def refresh(self):
        items = self.wrapper.data_manager.data["quarantine"]
        self.table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(item["original_path"]))
            self.table.setItem(i, 1, QTableWidgetItem(item["date"]))
            widget = QWidget()
            hl = QHBoxLayout(widget)
            hl.setContentsMargins(0, 0, 0, 0)
            c = DARK if self.is_dark else LIGHT
            for text, slot in [
                (self.trans.get("restore"), lambda ch, id=item["id"]: self.window().restore_file(id)),
                (self.trans.get("delete"),  lambda ch, id=item["id"]: self.window().delete_file(id)),
                (self.trans.get("view_code"), lambda ch, p=item["quarantine_path"]: self.window().view_code(p)),
            ]:
                btn = QPushButton(text)
                btn.setStyleSheet(f"background-color: {c['card2']}; color: {c['text']}; font-size: 10px; padding: 2px;")
                btn.clicked.connect(slot)
                hl.addWidget(btn)
            self.table.setCellWidget(i, 2, widget)


# ─────────────────────────────────────────────────────────
#  Settings View
# ─────────────────────────────────────────────────────────
class SettingsView(QWidget):
    def __init__(self, wrapper, trans, settings_manager, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.settings_manager = settings_manager
        self.is_dark = True
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll.setWidget(self.scroll_content)
        root_layout.addWidget(self.scroll)

        layout = QVBoxLayout(self.scroll_content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.title = QLabel()
        self.title.setObjectName("settingsTitle")
        layout.addWidget(self.title)

        # Language selection
        self.lang_card = QFrame()
        self.lang_card.setObjectName("settingsCard")
        l_layout = QVBoxLayout(self.lang_card)
        self.lbl_lang = QLabel()
        self.lbl_lang.setObjectName("settingsLabel")
        l_layout.addWidget(self.lbl_lang)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "Türkçe"])
        self.combo_lang.setCurrentIndex(0 if self.trans.lang == "en" else 1)
        l_layout.addWidget(self.combo_lang)
        layout.addWidget(self.lang_card)

        # Theme selection
        self.theme_card = QFrame()
        self.theme_card.setObjectName("settingsCard")
        t_layout = QVBoxLayout(self.theme_card)
        self.lbl_theme = QLabel()
        self.lbl_theme.setObjectName("settingsLabel")
        t_layout.addWidget(self.lbl_theme)
        self.combo_theme = QComboBox()
        t_layout.addWidget(self.combo_theme)
        layout.addWidget(self.theme_card)

        # VirusTotal API Key
        self.vt_card = QFrame()
        self.vt_card.setObjectName("settingsCard")
        v_layout = QVBoxLayout(self.vt_card)
        self.lbl_vt = QLabel()
        self.lbl_vt.setObjectName("settingsLabel")
        v_layout.addWidget(self.lbl_vt)
        
        self.edit_vt = QLineEdit()
        self.edit_vt.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_vt.setText(self.settings_manager.get("vt_api_key", ""))
        self.edit_vt.returnPressed.connect(self.save_all)
        v_layout.addWidget(self.edit_vt)
        v_layout.addSpacing(5)
        
        self.btn_vt_link = QPushButton()
        self.btn_vt_link.setObjectName("settingsLink")
        self.btn_vt_link.setFlat(True)
        self.btn_vt_link.setMinimumHeight(28)
        self.btn_vt_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vt_link.clicked.connect(self._open_vt_link)
        v_layout.addWidget(self.btn_vt_link, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.vt_card)

        # Breach Check Provider + Key
        self.breach_card = QFrame()
        self.breach_card.setObjectName("settingsCard")
        b_layout = QVBoxLayout(self.breach_card)

        self.lbl_breach_provider = QLabel()
        self.lbl_breach_provider.setObjectName("settingsLabel")
        b_layout.addWidget(self.lbl_breach_provider)

        self.combo_breach_provider = QComboBox()
        self.combo_breach_provider.setMinimumHeight(40)
        b_layout.addWidget(self.combo_breach_provider)

        b_layout.addSpacing(10)

        self.lbl_breach_key = QLabel()
        self.lbl_breach_key.setObjectName("settingsLabel")
        b_layout.addWidget(self.lbl_breach_key)

        self.edit_breach_key = QLineEdit()
        self.edit_breach_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_breach_key.setMinimumHeight(40)
        self.edit_breach_key.returnPressed.connect(self.save_all)
        b_layout.addWidget(self.edit_breach_key)
        b_layout.addSpacing(5)

        self.btn_breach_link = QPushButton()
        self.btn_breach_link.setObjectName("settingsLink")
        self.btn_breach_link.setFlat(True)
        self.btn_breach_link.setMinimumHeight(28)
        self.btn_breach_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_breach_link.clicked.connect(self._open_breach_provider_link)
        b_layout.addWidget(self.btn_breach_link, alignment=Qt.AlignmentFlag.AlignLeft)

        self.combo_breach_provider.currentIndexChanged.connect(self._on_breach_provider_changed)
        layout.addWidget(self.breach_card)

        # DB Update
        self.update_card = QFrame()
        self.update_card.setObjectName("settingsCard")
        up_layout = QVBoxLayout(self.update_card)
        self.bin_label = QLabel()
        self.bin_label.setObjectName("settingsLabel")
        up_layout.addWidget(self.bin_label)
        self.btn_update_db = QPushButton()
        self.btn_update_db.setObjectName("updateBtn")
        up_layout.addWidget(self.btn_update_db)
        layout.addWidget(self.update_card)

        # Global Save Button
        self.btn_save = QPushButton()
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.clicked.connect(self.save_all)
        layout.addWidget(self.btn_save)

        layout.addStretch()
        self.retranslate()

    def save_all(self):
        ok1, msg1 = self.settings_manager.set("vt_api_key", self.edit_vt.text())

        provider = "bd" if self.combo_breach_provider.currentIndex() == 0 else "hibp"
        self.settings_manager.set("breach_provider", provider)

        key_field = "bd_api_key" if provider == "bd" else "hibp_api_key"
        ok2, msg2 = self.settings_manager.set(key_field, self.edit_breach_key.text())

        if not ok1:
            QMessageBox.warning(self, "Error", msg1 or "Invalid settings value.")
            return
        if not ok2:
            QMessageBox.warning(self, "Error", msg2 or "Invalid settings value.")
            return
        msg = self.trans.get("save_settings_success") 
        if msg == "save_settings_success": msg = "Settings saved successfully."
        QMessageBox.information(self, "Success", msg)

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        
        # Avoid full auto-fill to prevent clashes with card backgrounds
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(c["bg"]))
        self.setPalette(pal)

        self.setStyleSheet(f"""
            QWidget {{ color: {c['text']}; }}
            #settingsTitle {{ font-size: 26px; font-weight: bold; color: {c['accent']}; margin-bottom: 5px; }}
            #settingsCard {{ background-color: {c['card']}; border-radius: 12px; padding: 15px 20px; }}
            #settingsLabel {{ font-size: 14px; font-weight: bold; color: {c['text']}; margin-bottom: 5px; }}
            #settingsLink {{ font-size: 13px; color: #89b4fa; border: none; background: transparent; 
                            text-align: left; padding: 8px 0px; text-decoration: underline; min-height: 28px; }}
            #settingsLink:hover {{ color: {c['accent']}; font-weight: bold; }}
            
            QComboBox {{ background-color: {c['bg']}; color: {c['text']}; padding: 0px 12px; 
                         border: 2px solid {c['card2']}; border-radius: 8px; font-size: 14px; min-height: 40px; }}
            QComboBox::drop-down {{ border: none; width: 0px; }}
            QComboBox QAbstractItemView {{ background-color: {c['card']}; selection-background-color: {c['accent']}; }}

            QLineEdit {{ background-color: {c['bg']}; color: {c['text']}; padding: 10px 12px; 
                         border: 2px solid {c['card2']}; border-radius: 8px; font-size: 14px; min-height: 40px; }}
            QLineEdit:focus {{ border-color: {c['accent']}; }}

            #updateBtn {{ background-color: {c['orange']}; color: #11111b; font-weight: bold; 
                         padding: 5px; border-radius: 8px; font-size: 14px; border: none; min-height: 44px; }}
            #updateBtn:hover {{ background-color: {c['accent']}; }}

            #saveBtn {{ background-color: {c['green']}; color: #11111b; font-weight: bold; 
                       padding: 10px; border-radius: 12px; font-size: 16px; border: none; margin-top: 10px; min-height: 52px; }}
            #saveBtn:hover {{ background-color: {c['accent']}; }}
        """)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        self.scroll_content.setStyleSheet(f"background-color: {c['bg']};")

    def _open_vt_link(self):
        url = self.trans.get('vt_key_link')
        QDesktopServices.openUrl(QUrl(url))

    def _open_breach_provider_link(self):
        provider = "bd" if self.combo_breach_provider.currentIndex() == 0 else "hibp"
        url = self.trans.get("bd_key_link") if provider == "bd" else self.trans.get("hibp_key_link")
        QDesktopServices.openUrl(QUrl(url))

    def _on_breach_provider_changed(self):
        provider = "bd" if self.combo_breach_provider.currentIndex() == 0 else "hibp"
        key_field = "bd_api_key" if provider == "bd" else "hibp_api_key"
        self.edit_breach_key.setText(self.settings_manager.get(key_field, "") or "")
        self._refresh_breach_provider_texts()

    def retranslate(self):
        self.title.setText(self.trans.get("settings_title"))
        self.lbl_lang.setText(self.trans.get("language"))
        self.lbl_theme.setText(self.trans.get("theme"))
        self.bin_label.setText(f"ClamAV binary: {self.wrapper.clamscan_path or 'Not Found'}")
        self.btn_update_db.setText(self.trans.get("update_db"))
        self.btn_save.setText(self.trans.get("save_settings"))
        self.lbl_vt.setText(self.trans.get("vt_api_key"))
        
        self.btn_vt_link.setText(f"➜ {self.trans.get('get_vt_key')}")
        # Provider combo items must be reloaded after language switch
        stored = (self.settings_manager.get("breach_provider", "bd") or "bd").strip().lower()
        cur_idx = 0 if stored == "bd" else 1
        self.combo_breach_provider.blockSignals(True)
        self.combo_breach_provider.clear()
        self.combo_breach_provider.addItems([
            self.trans.get("provider_option_bd"),
            self.trans.get("provider_option_hibp"),
        ])
        self.combo_breach_provider.setCurrentIndex(cur_idx)
        self.combo_breach_provider.blockSignals(False)

        key_field = "bd_api_key" if stored == "bd" else "hibp_api_key"
        self.edit_breach_key.setText(self.settings_manager.get(key_field, "") or "")
        self._refresh_breach_provider_texts()

        # Preserve combo selection
        idx = self.combo_theme.currentIndex()
        if idx < 0: idx = 0 
        self.combo_theme.blockSignals(True)
        self.combo_theme.clear()
        self.combo_theme.addItems([self.trans.get("dark_mode"), self.trans.get("light_mode")])
        self.combo_theme.setCurrentIndex(idx)
        self.combo_theme.blockSignals(False)

    def _refresh_breach_provider_texts(self):
        self.lbl_breach_provider.setText(self.trans.get("breach_provider"))
        self.lbl_breach_key.setText(self.trans.get("breach_provider_key"))
        provider = "bd" if self.combo_breach_provider.currentIndex() == 0 else "hibp"
        link_text = self.trans.get("get_bd_key") if provider == "bd" else self.trans.get("get_hibp_key")
        self.btn_breach_link.setText(f"➜ {link_text}")


# ─────────────────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wrapper = ClamWrapper()
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.wrapper.data_manager = DataManager(app_dir)
        self.settings_manager = SettingsManager()

        lang = self.wrapper.data_manager.data["settings"].get("language", "en")
        self.trans = Translations(lang)
        self.is_dark = self.wrapper.data_manager.data["settings"].get("theme", "dark") == "dark"

        self.scanner_thread = None
        self.current_infected = []
        self.setWindowTitle("ClamApp — Security Suite")
        self.resize(850, 650)
        self.setAcceptDrops(True)

        self.usb_guardian = USBGuardianLogic(callback=self.on_usb_detected)
        self.usb_guardian.start_monitoring()

        # App Icon
        icon_path = os.path.join(os.path.expanduser("~"), "Masaüstü", "clamapp.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Central
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = ModernSidebar(self.trans)
        main_layout.addWidget(self.sidebar)

        # ── Unified content area (one stack for all sections) ──
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area)

        # --- Antivirus section (sub-stack) ---
        self.dashboard = ScrollableDashboardView(self.wrapper, self.trans, self.wrapper.data_manager)
        self.scan_view = ScanView(self.wrapper, self.trans)
        self.results_view = ResultsSummaryView(self.wrapper, self.trans)
        self.quarantine_view = QuarantineView(self.wrapper, self.trans)
        self.schedule_view = ScheduleView(self.trans, self.settings_manager)

        self.antivirus_stack = QStackedWidget()
        self.antivirus_stack.addWidget(self.dashboard)        # 0
        self.antivirus_stack.addWidget(self.scan_view)        # 1
        self.antivirus_stack.addWidget(self.results_view)     # 2
        self.antivirus_stack.addWidget(self.quarantine_view)  # 3
        self.antivirus_stack.addWidget(self.schedule_view)    # 4 (Added for unified nav)

        # --- Cloud Scan ---
        self.cloud_view = CloudScanView(self.wrapper, self.trans, self.settings_manager)

        # --- Network View (separate sidebar section) ---
        self.network_view = NetworkView(self.trans)

        # --- Security Tools (inner-tabs, separate sidebar section) ---
        self.password_view = PasswordGeneratorView(self.trans)
        self.cipher_view = CipherView(self.trans)
        self.hash_view = HashToolView(self.trans)
        self.shredder_view = ShredderView(self.trans)
        self.vault_view = VaultView(self.trans)
        self.privacy_view = PrivacyView(self.trans)

        self.security_tabs = QTabWidget()
        self.security_tabs.setStyleSheet(self._tab_style(True))
        self.security_tabs.addTab(self.password_view, self.trans.get("password_gen"))
        self.security_tabs.addTab(self.cipher_view, self.trans.get("cipher_tool"))
        self.security_tabs.addTab(self.hash_view, self.trans.get("hash_tool"))
        self.security_tabs.addTab(self.shredder_view, self.trans.get("data_destroyer"))
        self.security_tabs.addTab(self.vault_view, self.trans.get("crypto_vault"))
        self.security_tabs.addTab(self.privacy_view, self.trans.get("privacy_shield"))

        # --- Settings view ---
        self.settings_view = SettingsView(self.wrapper, self.trans, self.settings_manager)

        # --- Security Modules ---
        self.breach_checker_view = BreachCheckerView(self.trans, self.settings_manager)
        self.firewall_view = FirewallView(self.trans)

        # Add all sections to content_area (unified stack)
        # Indices:
        #   0 = antivirus_stack
        #   1 = network_view
        #   2 = security_tabs
        #   3 = settings_view
        #   4 = cloud_view
        #   5 = breach_checker_view
        #   6 = firewall_view
        self.content_area.addWidget(self.antivirus_stack)     # 0
        self.content_area.addWidget(self.network_view)        # 1
        self.content_area.addWidget(self.security_tabs)       # 2
        self.content_area.addWidget(self.settings_view)       # 3
        self.content_area.addWidget(self.cloud_view)          # 4
        self.content_area.addWidget(self.breach_checker_view) # 5
        self.content_area.addWidget(self.firewall_view)       # 6

        # Wire up sidebar buttons
        self.sidebar.btn_dashboard.clicked.connect(lambda: self._show_antivirus(0))
        self.sidebar.btn_scan.clicked.connect(lambda: self._show_antivirus(1))
        self.sidebar.btn_quarantine.clicked.connect(lambda: self._show_antivirus(3))
        self.sidebar.btn_schedule.clicked.connect(lambda: self._show_antivirus(4))
        self.sidebar.btn_network.clicked.connect(lambda: self._show_section(1))
        self.sidebar.btn_cloud.clicked.connect(lambda: self._show_section(4))
        self.sidebar.btn_security.clicked.connect(lambda: self._show_section(2))
        self.sidebar.btn_settings.clicked.connect(lambda: self._show_settings())
        self.sidebar.btn_breach.clicked.connect(lambda: self._show_extra_section(5))
        self.sidebar.btn_firewall.clicked.connect(lambda: self._show_extra_section(6))

        # Wire up scan buttons
        self.results_view.btn_back.clicked.connect(lambda: self._show_antivirus(1))
        self.results_view.btn_action.clicked.connect(self.quarantine_all_results)
        self.scan_view.btn_quick.clicked.connect(self.start_quick_scan)
        self.scan_view.btn_full.clicked.connect(self.start_full_scan)
        self.scan_view.btn_custom.clicked.connect(self.start_custom_scan)
        self.scan_view.btn_stop.clicked.connect(self.stop_scan)

        self._check_first_run()

        # Wire up settings
        self.settings_view.btn_update_db.clicked.connect(self.run_update)
        self.settings_view.combo_lang.currentIndexChanged.connect(self.change_language)
        self.settings_view.combo_theme.currentIndexChanged.connect(self.change_theme)

        # Scheduling
        self.scheduler = ScheduleLogic(self.settings_manager)
        self.scheduler.trigger_scan.connect(self.on_scheduled_scan)
        self.scheduler.start()

        # Apply initial theme
        self.apply_theme(self.is_dark)

    def _check_first_run(self):
        if not self.settings_manager.get("first_run_done", False):
            msg = QMessageBox(self)
            msg.setWindowTitle(self.trans.get("first_run_title"))
            msg.setText(self.trans.get("first_run_body"))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.addButton(self.trans.get("first_run_btn"), QMessageBox.ButtonRole.AcceptRole)
            msg.exec()
            self.settings_manager.set("first_run_done", True)

    # ── Theme ──────────────────────────────────────────────────────────────

    def _tab_style(self, dark=True):
        c = DARK if dark else LIGHT
        return f"""
            QTabWidget::pane {{ border: none; background: {c['bg']}; }}
            QTabBar::tab {{
                background: {c['card']}; color: {c['text']};
                padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {c['accent']}; color: {'#11111b' if dark else '#ffffff'}; font-weight: bold; }}
            QTabBar::tab:hover {{ background: {c['card2']}; }}
        """

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        self.setStyleSheet(f"QMainWindow {{ background-color: {c['bg']}; }}")
        apply_palette(self, c)

        self.sidebar.apply_theme(dark)
        self.dashboard.apply_theme(dark)
        self.scan_view.apply_theme(dark)
        self.results_view.apply_theme(dark)
        self.quarantine_view.apply_theme(dark)
        self.schedule_view.apply_theme(dark)
        self.settings_view.apply_theme(dark)
        self.security_tabs.setStyleSheet(self._tab_style(dark))
        self.password_view.apply_theme(dark)
        self.cipher_view.apply_theme(dark)
        self.hash_view.apply_theme(dark)
        self.shredder_view.apply_theme(dark)
        self.vault_view.apply_theme(dark)
        self.privacy_view.apply_theme(dark)
        self.network_view.apply_theme(dark)
        self.cloud_view.apply_theme(dark)
        self.breach_checker_view.apply_theme(dark)
        self.firewall_view.apply_theme(dark)
        # Background of content area and stacked widgets
        for w in [self.content_area, self.antivirus_stack]:
            apply_palette(w, c)

    def change_theme(self, index):
        dark = index == 0
        self.wrapper.data_manager.data["settings"]["theme"] = "dark" if dark else "light"
        self.wrapper.data_manager.save_data()
        self.apply_theme(dark)

    # ── Language ───────────────────────────────────────────────────────────

    def change_language(self, index):
        lang = "en" if index == 0 else "tr"
        self.trans.lang = lang
        self.wrapper.data_manager.data["settings"]["language"] = lang
        self.wrapper.data_manager.save_data()
        self._retranslate_all()

    def _retranslate_all(self):
        self.sidebar.retranslate()
        self.dashboard.retranslate()
        self.scan_view.retranslate()
        self.results_view.retranslate()
        self.quarantine_view.retranslate()
        self.schedule_view.retranslate()
        self.settings_view.retranslate()
        self.password_view.retranslate()
        self.cipher_view.retranslate()
        self.hash_view.retranslate()
        self.shredder_view.retranslate()
        self.vault_view.retranslate()
        self.privacy_view.retranslate()
        self.network_view.retranslate()
        self.cloud_view.init_ui()  # Simple way to refresh labels
        self.breach_checker_view.retranslate()
        self.firewall_view.retranslate()
        self.security_tabs.setTabText(0, self.trans.get("password_gen"))
        self.security_tabs.setTabText(1, self.trans.get("cipher_tool"))
        self.security_tabs.setTabText(2, self.trans.get("hash_tool"))
        self.security_tabs.setTabText(3, self.trans.get("data_destroyer"))
        self.security_tabs.setTabText(4, self.trans.get("crypto_vault"))
        self.security_tabs.setTabText(5, self.trans.get("privacy_shield"))

    # ── Navigation ──────────────────────────────────────────────────────────

    def _uncheck_all_sidebar(self):
        """Decheck all sidebar nav buttons (without triggering signals)."""
        for btn in self.sidebar._all_nav_btns:
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.blockSignals(False)

    def _show_antivirus(self, stack_index):
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(0)  # antivirus_stack
        self.antivirus_stack.setCurrentIndex(stack_index)
        # Check the relevant sidebar button
        mapping = {0: self.sidebar.btn_dashboard, 1: self.sidebar.btn_scan, 3: self.sidebar.btn_quarantine, 4: self.sidebar.btn_schedule}
        btn = mapping.get(stack_index)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

    def _show_section(self, content_index):
        """Show network (1), security tools (2), or cloud (4) section."""
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(content_index)
        btn_map = {1: self.sidebar.btn_network, 2: self.sidebar.btn_security, 4: self.sidebar.btn_cloud}
        btn = btn_map.get(content_index)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

    def _show_extra_section(self, content_index):
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(content_index)
        if content_index == 6 and hasattr(self, "firewall_view"):
            # Always refresh firewall state when user opens the tab
            self.firewall_view.refresh_now()
        btn_map = {5: self.sidebar.btn_breach,
                   6: self.sidebar.btn_firewall}
        btn = btn_map.get(content_index)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

    def on_usb_detected(self, mount_point):
        reply = QMessageBox.question(self, self.trans.get("usb_detected"),
                                     self.trans.get("usb_scan_ask").format(mount_point),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._show_antivirus(1)
            self.run_scan(mount_point, "USB")

    def on_scheduled_scan(self):
        # Notify user
        from PyQt6.QtWidgets import QSystemTrayIcon
        tray = QSystemTrayIcon(self)
        tray.show()
        tray.showMessage("ClamApp", self.trans.get("scan_started_bg"))
        
        # Start full scan in background
        self._show_antivirus(1)
        self.start_full_scan()
        # When scan finishes, on_scan_finished will trigger a notification too (or we can add one there)

    def update_schedule(self):
        # Reset check so it can fire immediately if time matches
        self.last_sched_check = None

    def check_schedule(self):
        settings = self.wrapper.data_manager.data.get("settings", {})
        sched = settings.get("schedule", "none")
        if sched == "none":
            return
        
        target_time = settings.get("schedule_time", "03:00")
        now = QDateTime.currentDateTime()
        now_time = now.toString("HH:mm")
        
        if now_time == target_time:
            # Avoid multiple triggers in the same minute
            if self.last_sched_check == now.date().toString():
                return
            
            day_of_week = now.date().dayOfWeek() # 1-7 (Mon-Sun)
            if sched == "weekly" and day_of_week != 1: # Only Mondays
                return
                
            self.last_sched_check = now.date().toString()
            self._show_antivirus(1)
            self.start_full_scan()

    def _show_settings(self):
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(3)  # settings_view
        self.sidebar.btn_settings.blockSignals(True)
        self.sidebar.btn_settings.setChecked(True)
        self.sidebar.btn_settings.blockSignals(False)

    # ── Scan ───────────────────────────────────────────────────────────────

    def start_quick_scan(self):
        self.run_scan(os.path.expanduser("~"), "Quick")

    def start_full_scan(self):
        self.run_scan("/", "Full")

    def start_custom_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if folder:
            self.run_scan(folder, "Custom")

    def run_scan(self, path, scan_type="Custom"):
        if not self.wrapper.clamscan_path:
            QMessageBox.critical(self, "Error", "ClamAV binary not found!")
            return
        self.current_scan_type = scan_type
        self.current_scan_path = path
        self.scan_view.options_widget.setDisabled(True)
        self.scan_view.progress_frame.setHidden(False)
        self.scan_view.progress_label.setText(f"{self.trans.get('scanning')} {path}...")
        self.scan_view.progress_bar.setRange(0, 0)
        self.scanner_thread = ScannerThread(self.wrapper.clamscan_path, path)
        self.scanner_thread.finished.connect(self.on_scan_finished)
        self.scanner_thread.progress.connect(
            lambda msg: self.scan_view.progress_label.setText(msg[:120])
        )

        self.scanner_thread.start()

    def on_scan_finished(self, results):
        self.scan_view.options_widget.setDisabled(False)
        self.scan_view.progress_frame.setHidden(True)
        infected_files = []
        if results["status"] == "infected":
            for line in results["output"].splitlines():
                if "FOUND" in line:
                    infected_files.append(line.split(":")[0].strip())
        self.results_view.show_results(infected_files, results.get("output", ""))
        self._show_antivirus(2)
        self.current_infected = infected_files
        self.wrapper.data_manager.add_scan_result(len(infected_files), 100, self.current_scan_type, self.current_scan_path)
        self.dashboard.refresh_stats()
        self.scan_view.refresh_history()

    # ── Quarantine ─────────────────────────────────────────────────────────

    def quarantine_all_results(self):
        failed = []
        succeeded = 0
        for f in self.current_infected:
            try:
                success, message = self.wrapper.data_manager.secure_quarantine(f)
                if success:
                    succeeded += 1
                else:
                    failed.append(f"{os.path.basename(f)}: {message}")
            except (OSError, PermissionError) as exc:
                failed.append(f"{os.path.basename(f)}: {exc}")

        self.quarantine_view.refresh()

        if failed:
            err_list = "\n".join(failed)
            QMessageBox.warning(
                self, "Quarantine Partial Failure",
                f"{succeeded} file(s) quarantined successfully.\n\nFailed:\n{err_list}"
            )
        else:
            QMessageBox.information(
                self, "Quarantine Complete",
                f"{succeeded} file(s) quarantined. Permissions stripped (chmod 0o000). "
                f"Metadata saved to ~/.clamapp/quarantine/."
            )
        self._show_antivirus(3)

    def restore_file(self, file_id):
        try:
            success, message = self.wrapper.data_manager.restore_file(file_id)
            if success:
                self.quarantine_view.refresh()
                QMessageBox.information(self, "Restored", message)
            else:
                QMessageBox.warning(self, "Restore Failed", message)
        except (OSError, PermissionError) as exc:
            QMessageBox.warning(self, "Permission Error",
                                f"Could not restore file: {exc}")

    def delete_file(self, file_id):
        try:
            success, message = self.wrapper.data_manager.delete_permanently(file_id)
            if success:
                self.quarantine_view.refresh()
            else:
                QMessageBox.warning(self, "Delete Failed", message)
        except (OSError, PermissionError) as exc:
            QMessageBox.warning(self, "Permission Error",
                                f"Could not delete file: {exc}")


    def view_code(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Error", "File not found.")
            return

        size_bytes = os.path.getsize(path)
        size_mb = size_bytes / (1024 * 1024)
        limit = None
        
        if size_bytes > 1024 * 1024:
            # Large file handling
            msg = f"This file is large ({size_mb:.2f} MB). Loading it completely might freeze the application. " \
                  f"Would you like to load the first 100KB (Preview) or the Whole File?"
            
            box = QMessageBox(self)
            box.setWindowTitle(self.trans.get("large_file"))
            box.setText(msg)
            btn_preview = box.addButton("Preview (100KB)", QMessageBox.ButtonRole.ActionRole)
            btn_whole = box.addButton("Whole File", QMessageBox.ButtonRole.ActionRole)
            btn_cancel = box.addButton(QMessageBox.StandardButton.Cancel)
            
            box.exec()
            
            if box.clickedButton() == btn_preview:
                limit = 100 * 1024
            elif box.clickedButton() == btn_whole:
                limit = None
            else:
                return

        # Show progress if it's large and we are loading the whole thing
        if limit is None and size_bytes > 2 * 1024 * 1024:
            progress = QProgressDialog("Loading file content...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()

        success, content, is_binary = self.wrapper.data_manager.secure_read_file(path, limit=limit)
        
        if success:
            dlg = CodeViewerDialog(
                self.trans.get("safe_viewer") + f" - {os.path.basename(path)}", 
                content, 
                self.trans, 
                is_binary=is_binary, 
                parent=self
            )
            dlg.exec()
        else:
            QMessageBox.warning(self, "Error", content)

    # ── DB Update ───────────────────────────────────────────────────────────

    def run_update(self):
        self.settings_view.btn_update_db.setText(self.trans.get("updating"))
        self.settings_view.btn_update_db.setDisabled(True)
        self._db_thread = DbUpdateThread(self.wrapper, parent=self)
        self._db_thread.finished.connect(self._on_update_finished)
        self._db_thread.start()

    def _on_update_finished(self, result):
        if result["status"] == "success":
            QMessageBox.information(self, "Update", result["message"])
        else:
            QMessageBox.warning(self, "Update", result["message"])
        self.settings_view.btn_update_db.setText(self.trans.get("update_db"))
        self.settings_view.btn_update_db.setDisabled(False)
        self.dashboard.db_label.setText(
            f"{self.trans.get('last_update')}: {self.wrapper.get_database_info()}"
        )


    # ── Stop Scan ───────────────────────────────────────────────────────────

    def stop_scan(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
        self.scan_view.options_widget.setDisabled(False)
        self.scan_view.progress_frame.setHidden(True)

    # ── Drag & Drop ──────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self._show_antivirus(1)
            self.run_scan(files[0], "Drag & Drop")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
