from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.security_audit import SecurityAuditLogic

class AuditView(QWidget):
    def __init__(self, trans, data_manager, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.logic = SecurityAuditLogic(data_manager)
        self.init_ui()
        QTimer.singleShot(500, self.run_audit)

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#1e66f5"
        
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.score_card.setStyleSheet(f"background-color: {card}; border-radius: 50px; border: 2px solid {accent};")
        self.score_lbl.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {text};")
        
        for frame in self.check_frames:
            frame.setStyleSheet(f"background-color: {card}; border-radius: 10px; padding: 15px;")
        for lbl in self.check_labels:
            lbl.setStyleSheet(f"color: {text}; font-size: 14px;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        self.title = QLabel("Security Audit")
        layout.addWidget(self.title)

        # Score Circle
        self.score_container = QHBoxLayout()
        self.score_card = QFrame()
        self.score_card.setFixedSize(180, 180)
        score_layout = QVBoxLayout(self.score_card)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.score_lbl = QLabel("--")
        score_layout.addWidget(self.score_lbl)
        
        score_title = QLabel("Security Score")
        score_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(score_title)
        
        self.score_container.addStretch()
        self.score_container.addWidget(self.score_card)
        self.score_container.addStretch()
        layout.addLayout(self.score_container)

        # Checks Grid
        self.grid = QGridLayout()
        self.check_frames = []
        self.check_labels = []
        self.check_status_labels = []

        self.add_check(0, 0, "Firewall (UFW)", "ufw_status")
        self.add_check(0, 1, "SSH Port (22)", "ssh_status")
        self.add_check(1, 0, "Last Scan", "scan_age")
        self.add_check(1, 1, "System Updates", "update_status")

        layout.addLayout(self.grid)

        self.btn_refresh = QPushButton("Re-Run Audit")
        self.btn_refresh.clicked.connect(self.run_audit)
        self.btn_refresh.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 12px; border-radius: 8px;")
        layout.addWidget(self.btn_refresh)
        
        layout.addStretch()

    def add_check(self, r, c, title, key):
        frame = QFrame()
        l = QVBoxLayout(frame)
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.check_labels.append(t_lbl)
        
        s_lbl = QLabel("Checking...")
        self.check_status_labels.append(s_lbl)
        
        l.addWidget(t_lbl)
        l.addWidget(s_lbl)
        
        self.grid.addWidget(frame, r, c)
        self.check_frames.append(frame)
        setattr(self, f"lbl_{key}", s_lbl)

    def run_audit(self):
        self.btn_refresh.setEnabled(False)
        res = self.logic.perform_audit()
        
        self.score_lbl.setText(str(res["score"]))
        
        # Color score
        if res["score"] > 80: color = "#a6e3a1"
        elif res["score"] > 50: color = "#fab387"
        else: color = "#f38ba8"
        self.score_lbl.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")

        self.lbl_ufw_status.setText("Enabled" if res["ufw"] else "Disabled")
        self.lbl_ufw_status.setStyleSheet(f"color: {'#a6e3a1' if res['ufw'] else '#f38ba8'}; font-weight: bold;")
        
        self.lbl_ssh_status.setText("Open" if res["ssh"] else "Closed")
        self.lbl_ssh_status.setStyleSheet(f"color: {'#f38ba8' if res['ssh'] else '#a6e3a1'}; font-weight: bold;")
        
        days = res["last_scan"]
        self.lbl_scan_age.setText(f"{days} days ago" if days < 999 else "Never")
        self.lbl_scan_age.setStyleSheet(f"color: {'#a6e3a1' if days <= 7 else '#f38ba8'}; font-weight: bold;")
        
        self.lbl_update_status.setText("Up to date (mock)")
        self.lbl_update_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")

        self.btn_refresh.setEnabled(True)

    def retranslate(self):
        self.title.setText(self.trans.get("security_audit"))
        self.btn_refresh.setText(self.trans.get("rerun_audit"))
        # More translation updates here later
