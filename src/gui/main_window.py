from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget,
                             QProgressBar, QMessageBox, QFileDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox, QDialog, QTextEdit,
                             QTabWidget, QSplitter, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QFont, QIcon, QColor, QDragEnterEvent, QDropEvent, QPalette
import os
import sys
import stat

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
from gui.cleaner_view import CleanerView
from gui.audit_view import AuditView
from gui.startup_view import StartupView
from gui.app_manager_view import AppManagerView
from gui.task_manager_view import TaskManagerView

from modules.usb_guardian import USBGuardianLogic

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
    def __init__(self, title, content, translations, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        layout = QVBoxLayout(self)
        warn = QLabel(translations.get("safe_viewer_warn"))
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #f38ba8; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(warn)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(content)
        te.setStyleSheet("background-color: #181825; border: 1px solid #45475a; font-family: monospace;")
        layout.addWidget(te)
        btn = QPushButton(translations.get("close"))
        btn.setStyleSheet("background-color: #45475a; color: #cdd6f4; padding: 10px; border-radius: 5px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ─────────────────────────────────────────────────────────
#  Modern Sidebar
# ─────────────────────────────────────────────────────────
class ModernSidebar(QFrame):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.setFixedWidth(200)
        self._setup()

    def _btn_style(self, c):
        return f"""
            QPushButton {{ background-color: transparent; color: {c['text']};
                border: none; padding: 15px; text-align: left; font-size: 14px;
                border-radius: 5px; margin: 5px; }}
            QPushButton:hover   {{ background-color: {c['btn_hover']}; }}
            QPushButton:checked {{ background-color: {c['btn_checked']}; color: {c['accent']}; font-weight: bold; }}
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

        # Separator label
        self.sep_label = QLabel()
        self.sep_label.setFixedHeight(1)
        self.sep_label.setStyleSheet("background-color: #313244; margin: 4px 10px;")

        self.btn_network = QPushButton(f"🌐 {self.trans.get('active_connections')}")
        self.btn_network.setCheckable(True)

        self.btn_security = QPushButton(f"🔒 {self.trans.get('security_tools')}")
        self.btn_security.setCheckable(True)

        self.btn_cleaner = QPushButton(f"🧹 {self.trans.get('system_hygiene')}")
        self.btn_cleaner.setCheckable(True)

        self.btn_audit = QPushButton(f"📋 {self.trans.get('security_audit')}")
        self.btn_audit.setCheckable(True)

        self.btn_startup = QPushButton(f"🚀 {self.trans.get('startup_manager')}")
        self.btn_startup.setCheckable(True)

        self.btn_apps = QPushButton(f"📦 {self.trans.get('app_manager')}")
        self.btn_apps.setCheckable(True)

        self.btn_tasks = QPushButton(f"📊 {self.trans.get('task_manager')}")
        self.btn_tasks.setCheckable(True)

        self.btn_settings = QPushButton(f"⚙ {self.trans.get('settings')}")
        self.btn_settings.setCheckable(True)

        for btn in [self.btn_dashboard, self.btn_scan, self.btn_quarantine]:
            layout.addWidget(btn)
        layout.addWidget(self.sep_label)
        for btn in [self.btn_network, self.btn_security, self.btn_cleaner, self.btn_audit, self.btn_startup, self.btn_apps, self.btn_tasks]:
            layout.addWidget(btn)
        layout.addStretch()
        layout.addWidget(self.btn_settings)

        self.version_label = QLabel("v0.3.0")
        self.version_label.setStyleSheet("color: #585b70; padding: 10px;")
        layout.addWidget(self.version_label)
        self.apply_theme(True)

    @property
    def _all_nav_btns(self):
        return [self.btn_dashboard, self.btn_scan, self.btn_quarantine,
                self.btn_network, self.btn_security, self.btn_cleaner,
                self.btn_audit, self.btn_startup, self.btn_apps, self.btn_tasks, self.btn_settings]

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
        self.btn_network.setText(f"🌐 {self.trans.get('active_connections')}")
        self.btn_security.setText(f"🔒 {self.trans.get('security_tools')}")
        self.btn_cleaner.setText(f"🧹 {self.trans.get('system_hygiene')}")
        self.btn_audit.setText(f"📋 {self.trans.get('security_audit')}")
        self.btn_startup.setText(f"🚀 {self.trans.get('startup_manager')}")
        self.btn_apps.setText(f"📦 {self.trans.get('app_manager')}")
        self.btn_tasks.setText(f"📊 {self.trans.get('task_manager')}")
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
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #45475a; border-radius: 5px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #89b4fa; }
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
    def __init__(self, wrapper, trans, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.is_dark = True
        layout = QVBoxLayout(self)

        self.title = QLabel()
        self.title.setStyleSheet("color: #cdd6f4; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.title)

        # Language
        lang_card = QFrame()
        lang_card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px; margin-bottom: 10px;")
        l_layout = QHBoxLayout(lang_card)
        self.lbl_lang = QLabel(self.trans.get("language"))
        l_layout.addWidget(self.lbl_lang)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "Türkçe"])
        current_lang = self.wrapper.data_manager.data["settings"].get("language", "en")
        self.combo_lang.setCurrentIndex(0 if current_lang == "en" else 1)
        l_layout.addWidget(self.combo_lang)
        layout.addWidget(lang_card)

        # Theme
        theme_card = QFrame()
        theme_card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px; margin-bottom: 10px;")
        t_layout = QHBoxLayout(theme_card)
        self.lbl_theme = QLabel(self.trans.get("theme"))
        t_layout.addWidget(self.lbl_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([self.trans.get("dark_mode"), self.trans.get("light_mode")])
        current_theme = self.wrapper.data_manager.data["settings"].get("theme", "dark")
        self.combo_theme.setCurrentIndex(0 if current_theme == "dark" else 1)
        t_layout.addWidget(self.combo_theme)
        layout.addWidget(theme_card)

        # DB Update
        update_card = QFrame()
        update_card.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 20px;")
        up_layout = QVBoxLayout(update_card)
        self.bin_label = QLabel()
        up_layout.addWidget(self.bin_label)
        self.btn_update_db = QPushButton()
        self.btn_update_db.setStyleSheet("""
            QPushButton { background-color: #fab387; color: #11111b; font-weight: bold;
                border-radius: 5px; padding: 10px; margin-top: 10px; }
            QPushButton:hover { background-color: #ef9f76; }
        """)
        up_layout.addWidget(self.btn_update_db)
        layout.addWidget(update_card)

        self.lang_card = lang_card
        self.theme_card = theme_card
        self.update_card = update_card
        self.retranslate()
        layout.addStretch()

    def apply_theme(self, dark=True):
        self.is_dark = dark
        c = DARK if dark else LIGHT
        apply_palette(self, c)
        self.title.setStyleSheet(f"color: {c['text']}; font-size: 24px; font-weight: bold;")
        for card in [self.lang_card, self.theme_card, self.update_card]:
            card.setStyleSheet(f"background-color: {c['card']}; border-radius: 10px; padding: 20px; margin-bottom: 10px;")
        for lbl in [self.lbl_lang, self.lbl_theme, self.bin_label]:
            lbl.setStyleSheet(f"color: {c['text']};")
        for combo in [self.combo_lang, self.combo_theme]:
            combo.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']}; padding: 4px;")

    def retranslate(self):
        self.title.setText(self.trans.get("settings_title"))
        self.lbl_lang.setText(self.trans.get("language"))
        self.lbl_theme.setText(self.trans.get("theme"))
        self.bin_label.setText(f"ClamAV binary: {self.wrapper.clamscan_path or 'Not Found'}")
        self.btn_update_db.setText(self.trans.get("update_db"))
        # Preserve combo selection while updating labels
        idx = self.combo_theme.currentIndex()
        self.combo_theme.blockSignals(True)
        self.combo_theme.clear()
        self.combo_theme.addItems([self.trans.get("dark_mode"), self.trans.get("light_mode")])
        self.combo_theme.setCurrentIndex(idx)
        self.combo_theme.blockSignals(False)


# ─────────────────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wrapper = ClamWrapper()
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.wrapper.data_manager = DataManager(app_dir)

        lang = self.wrapper.data_manager.data["settings"].get("language", "en")
        self.trans = Translations(lang)
        self.is_dark = self.wrapper.data_manager.data["settings"].get("theme", "dark") == "dark"

        self.scanner_thread = None
        self.current_infected = []
        self.setWindowTitle("ClamApp — Security Suite")
        self.resize(1200, 780)
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
        self.dashboard = DashboardView(self.wrapper, self.trans)
        self.scan_view = ScanView(self.wrapper, self.trans)
        self.results_view = ResultsSummaryView(self.wrapper, self.trans)
        self.quarantine_view = QuarantineView(self.wrapper, self.trans)

        self.antivirus_stack = QStackedWidget()
        self.antivirus_stack.addWidget(self.dashboard)        # 0
        self.antivirus_stack.addWidget(self.scan_view)        # 1
        self.antivirus_stack.addWidget(self.results_view)     # 2
        self.antivirus_stack.addWidget(self.quarantine_view)  # 3

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
        self.settings_view = SettingsView(self.wrapper, self.trans)

        # --- New Expanded Modules ---
        self.cleaner_view = CleanerView(self.trans)
        self.audit_view = AuditView(self.trans, self.wrapper.data_manager)
        self.startup_view = StartupView(self.trans)
        self.app_manager_view = AppManagerView(self.trans)
        self.task_manager_view = TaskManagerView(self.trans)

        # Add all sections to content_area (unified stack)
        # Indices:
        #   0 = antivirus_stack
        #   1 = network_view
        #   2 = security_tabs
        #   3 = settings_view
        #   4 = cleaner_view
        #   5 = audit_view
        #   6 = startup_view
        #   7 = app_manager_view
        #   8 = task_manager_view
        self.content_area.addWidget(self.antivirus_stack)  # 0
        self.content_area.addWidget(self.network_view)     # 1
        self.content_area.addWidget(self.security_tabs)    # 2
        self.content_area.addWidget(self.settings_view)    # 3
        self.content_area.addWidget(self.cleaner_view)     # 4
        self.content_area.addWidget(self.audit_view)       # 5
        self.content_area.addWidget(self.startup_view)     # 6
        self.content_area.addWidget(self.app_manager_view) # 7
        self.content_area.addWidget(self.task_manager_view) # 8

        # Wire up sidebar buttons
        self.sidebar.btn_dashboard.clicked.connect(lambda: self._show_antivirus(0))
        self.sidebar.btn_scan.clicked.connect(lambda: self._show_antivirus(1))
        self.sidebar.btn_quarantine.clicked.connect(lambda: self._show_antivirus(3))
        self.sidebar.btn_network.clicked.connect(lambda: self._show_section(1))
        self.sidebar.btn_security.clicked.connect(lambda: self._show_section(2))
        self.sidebar.btn_settings.clicked.connect(lambda: self._show_settings())
        self.sidebar.btn_cleaner.clicked.connect(lambda: self._show_extra_section(4))
        self.sidebar.btn_audit.clicked.connect(lambda: self._show_extra_section(5))
        self.sidebar.btn_startup.clicked.connect(lambda: self._show_extra_section(6))
        self.sidebar.btn_apps.clicked.connect(lambda: self._show_extra_section(7))
        self.sidebar.btn_tasks.clicked.connect(lambda: self._show_extra_section(8))

        # Wire up scan buttons
        self.results_view.btn_back.clicked.connect(lambda: self._show_antivirus(1))
        self.results_view.btn_action.clicked.connect(self.quarantine_all_results)
        self.scan_view.btn_quick.clicked.connect(self.start_quick_scan)
        self.scan_view.btn_full.clicked.connect(self.start_full_scan)
        self.scan_view.btn_custom.clicked.connect(self.start_custom_scan)
        self.scan_view.btn_stop.clicked.connect(self.stop_scan)

        # Wire up settings
        self.settings_view.btn_update_db.clicked.connect(self.run_update)
        self.settings_view.combo_lang.currentIndexChanged.connect(self.change_language)
        self.settings_view.combo_theme.currentIndexChanged.connect(self.change_theme)

        # Apply initial theme
        self.apply_theme(self.is_dark)

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
        self.settings_view.apply_theme(dark)
        self.security_tabs.setStyleSheet(self._tab_style(dark))
        self.password_view.apply_theme(dark)
        self.cipher_view.apply_theme(dark)
        self.hash_view.apply_theme(dark)
        self.shredder_view.apply_theme(dark)
        self.vault_view.apply_theme(dark)
        self.privacy_view.apply_theme(dark)
        self.network_view.apply_theme(dark)
        self.cleaner_view.apply_theme(dark)
        self.audit_view.apply_theme(dark)
        self.startup_view.apply_theme(dark)
        self.app_manager_view.apply_theme(dark)
        self.task_manager_view.apply_theme(dark)
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
        self.settings_view.retranslate()
        self.password_view.retranslate()
        self.cipher_view.retranslate()
        self.hash_view.retranslate()
        self.shredder_view.retranslate()
        self.vault_view.retranslate()
        self.privacy_view.retranslate()
        self.network_view.retranslate()
        self.cleaner_view.retranslate()
        self.audit_view.retranslate()
        self.startup_view.retranslate()
        self.app_manager_view.retranslate()
        self.task_manager_view.retranslate()
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
        mapping = {0: self.sidebar.btn_dashboard, 1: self.sidebar.btn_scan, 3: self.sidebar.btn_quarantine}
        btn = mapping.get(stack_index)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

    def _show_section(self, content_index):
        """Show network (1) or security tools (2) section."""
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(content_index)
        btn = self.sidebar.btn_network if content_index == 1 else self.sidebar.btn_security
        btn.blockSignals(True)
        btn.setChecked(True)
        btn.blockSignals(False)

    def _show_extra_section(self, content_index):
        self._uncheck_all_sidebar()
        self.content_area.setCurrentIndex(content_index)
        btn_map = {4: self.sidebar.btn_cleaner, 5: self.sidebar.btn_audit, 
                   6: self.sidebar.btn_startup, 7: self.sidebar.btn_apps,
                   8: self.sidebar.btn_tasks}
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
        for f in self.current_infected:
            # Secure the quarantined file: move then strip executable permissions
            success = self.wrapper.data_manager.quarantine_file(f)
            if success:
                q_items = self.wrapper.data_manager.data["quarantine"]
                if q_items:
                    q_path = q_items[-1]["quarantine_path"]
                    try:
                        # Strip all execute bits and make it read-only
                        os.chmod(q_path, stat.S_IRUSR)
                    except Exception:
                        pass
        self.quarantine_view.refresh()
        QMessageBox.information(self, "Success", "Items moved to quarantine. Execute permissions stripped.")
        self._show_antivirus(3)

    def restore_file(self, id):
        if self.wrapper.data_manager.restore_file(id):
            self.quarantine_view.refresh()
        else:
            QMessageBox.warning(self, "Error", "Failed to restore file.")

    def delete_file(self, id):
        if self.wrapper.data_manager.delete_permanently(id):
            self.quarantine_view.refresh()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete file.")

    def view_code(self, path):
        content = self.wrapper.get_file_content(path)
        dlg = CodeViewerDialog(self.trans.get("safe_viewer"), content, self.trans)
        dlg.exec()

    # ── DB Update ───────────────────────────────────────────────────────────

    def run_update(self):
        self.settings_view.btn_update_db.setText(self.trans.get("updating"))
        self.settings_view.btn_update_db.setDisabled(True)
        res = self.wrapper.update_database()
        if res["status"] == "success":
            QMessageBox.information(self, "Update", res["message"])
        else:
            QMessageBox.warning(self, "Update", res["message"])
        self.settings_view.btn_update_db.setText(self.trans.get("update_db"))
        self.settings_view.btn_update_db.setDisabled(False)
        self.dashboard.db_label.setText(f"{self.trans.get('last_update')}: {self.wrapper.get_database_info()}")

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
