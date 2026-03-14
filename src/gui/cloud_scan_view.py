from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QFrame, QScrollArea, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor
import os
import sys

if os.path.dirname(os.path.dirname(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.vt_service import VTService

class CloudScanThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, service, file_path, action="report"):
        super().__init__()
        self.service = service
        self.file_path = file_path
        self.action = action

    def run(self):
        if self.action == "report":
            h = self.service.get_file_hash(self.file_path)
            if not h:
                self.finished.emit({"error": "Could not calculate hash"})
                return
            res = self.service.get_report(h)
            res["hash"] = h
            self.finished.emit(res)
        elif self.action == "upload":
            res = self.service.upload_file(self.file_path)
            self.finished.emit(res)

class CloudScanView(QWidget):
    def __init__(self, wrapper, trans, settings_manager, parent=None):
        super().__init__(parent)
        self.wrapper = wrapper
        self.trans = trans
        self.settings_manager = settings_manager
        self.vt_service = VTService()
        self.current_file = None
        self.init_ui()

    def apply_theme(self, dark=True):
        if dark:
            bg, card, text, accent = "#181825", "#313244", "#cdd6f4", "#89b4fa"
        else:
            bg, card, text, accent = "#eff1f5", "#ccd0da", "#4c4f69", "#1e66f5"
        
        self.setStyleSheet(f"background-color: {bg}; color: {text};")
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.drop_frame.setStyleSheet(f"QFrame {{ border: 2px dashed {accent}; border-radius: 10px; background-color: {card}; }}")
        self.results_card.setStyleSheet(f"background-color: {card}; border-radius: 12px; padding: 20px;")
        self.detections_table.setStyleSheet(f"background-color: {card}; color: {text}; border: none;")
        self.stats_table.setStyleSheet(f"background-color: {card}; color: {text}; border: none;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.title = QLabel("Cloud Scan (VirusTotal)")
        layout.addWidget(self.title)

        # Drop Area
        self.drop_frame = QFrame()
        self.drop_frame.setFixedHeight(150)
        self.drop_frame.setAcceptDrops(True)
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.drop_label = QLabel("Drag & Drop file here or Click to Browse")
        self.drop_label.setStyleSheet("font-size: 16px;")
        drop_layout.addWidget(self.drop_label)
        
        layout.addWidget(self.drop_frame)
        self.drop_frame.mousePressEvent = lambda e: self.browse_file()

        # Results area
        self.results_card = QFrame()
        self.results_card.setVisible(False)
        res_layout = QVBoxLayout(self.results_card)
        
        self.lbl_status = QLabel("Scanning...")
        self.lbl_status.setStyleSheet("font-size: 18px; font-weight: bold;")
        res_layout.addWidget(self.lbl_status)
        
        self.lbl_hash = QLabel("")
        self.lbl_hash.setStyleSheet("font-family: monospace; font-size: 12px;")
        self.lbl_hash.setWordWrap(True)
        res_layout.addWidget(self.lbl_hash)
        
        self.stats_table = QTableWidget(0, 2)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.horizontalHeader().setVisible(False)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setFixedHeight(120)
        res_layout.addWidget(self.stats_table)
        
        self.lbl_detections = QLabel("Detailed Detections:")
        self.lbl_detections.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.lbl_detections.setVisible(False)
        res_layout.addWidget(self.lbl_detections)
        
        self.detections_table = QTableWidget(0, 2)
        self.detections_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.detections_table.setHorizontalHeaderLabels(["Engine", "Detection"])
        self.detections_table.verticalHeader().setVisible(False)
        self.detections_table.setVisible(False)
        self.detections_table.setMinimumHeight(200)
        res_layout.addWidget(self.detections_table)
        
        # Action Buttons
        btn_action_layout = QHBoxLayout()
        
        self.btn_quarantine = QPushButton("Quarantine File")
        self.btn_quarantine.setVisible(False)
        self.btn_quarantine.clicked.connect(self.quarantine_current_file)
        self.btn_quarantine.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        btn_action_layout.addWidget(self.btn_quarantine)

        self.btn_upload = QPushButton("Upload to VirusTotal")
        self.btn_upload.setVisible(False)
        self.btn_upload.clicked.connect(self.start_upload)
        self.btn_upload.setStyleSheet("background-color: #fab387; color: #11111b; font-weight: bold; padding: 10px; border-radius: 6px;")
        btn_action_layout.addWidget(self.btn_upload)
        
        res_layout.addLayout(btn_action_layout)
        
        layout.addWidget(self.results_card)
        layout.addStretch()

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File for Cloud Scan")
        if path:
            self.start_scan(path)

    def start_scan(self, path):
        api_key = self.settings_manager.get("vt_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Configuration not found", 
                                "Configuration not found. Please go to Settings and enter your VirusTotal API Key.")
            return

        self.current_file = path
        self.vt_service.set_api_key(api_key)
        self.results_card.setVisible(True)
        self.lbl_status.setText("Checking VirusTotal...")
        self.lbl_hash.setText("Calculating Hash...")
        self.btn_upload.setVisible(False)
        self.btn_quarantine.setVisible(False)
        self.stats_table.setRowCount(0)
        self.detections_table.setRowCount(0)
        self.detections_table.setVisible(False)
        self.lbl_detections.setVisible(False)
        
        self.thread = CloudScanThread(self.vt_service, path, "report")
        self.thread.finished.connect(self.on_report_finished)
        self.thread.start()

    def on_report_finished(self, res):
        if "error" in res:
            self.lbl_status.setText(f"Error: {res['error']}")
            return

        self.lbl_hash.setText(f"SHA256: {res.get('hash', 'N/A')}")
        
        if res.get("not_found"):
            self.lbl_status.setText("File not found on VirusTotal.")
            self.btn_upload.setVisible(True)
            return

        # Parse results
        data = res.get("data", {})
        attr = data.get("attributes", {})
        stats = attr.get("last_analysis_stats", {})
        results = attr.get("last_analysis_results", {})
        
        # Collect malicious engine names
        malicious_engines = []
        for engine, detail in results.items():
            if detail.get("category") == "malicious":
                malicious_engines.append(engine)
        
        self.lbl_status.setText(f"Detections: {stats.get('malicious', 0)} / {sum(stats.values())} engines")
        if stats.get('malicious', 0) > 0:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #f38ba8;")
            self.btn_quarantine.setVisible(True)
        else:
            self.lbl_status.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1;")
            self.btn_quarantine.setVisible(True) # Optional quarantine even if clean

        # Fill detection table
        if malicious_engines:
            self.lbl_detections.setVisible(True)
            self.detections_table.setVisible(True)
            self.detections_table.setRowCount(len(malicious_engines))
            for i, engine in enumerate(malicious_engines):
                detail = results.get(engine, {})
                result_text = detail.get("result", "Malicious")
                self.detections_table.setItem(i, 0, QTableWidgetItem(engine))
                item_res = QTableWidgetItem(result_text)
                item_res.setForeground(QColor("#f38ba8"))
                self.detections_table.setItem(i, 1, item_res)
        else:
            self.lbl_detections.setVisible(False)
            self.detections_table.setVisible(False)

        # Fill table with details
        self.stats_table.setRowCount(len(stats))
        for i, (k, v) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, QTableWidgetItem(k.capitalize()))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(v)))

    def start_upload(self):
        self.lbl_status.setText("Uploading file...")
        self.btn_upload.setEnabled(False)
        self.thread = CloudScanThread(self.vt_service, self.current_file, "upload")
        self.thread.finished.connect(self.on_upload_finished)
        self.thread.start()

    def on_upload_finished(self, res):
        self.btn_upload.setEnabled(True)
        if "error" in res:
            self.lbl_status.setText(f"Upload Error: {res['error']}")
        else:
            self.lbl_status.setText("File uploaded for analysis. Please check back in a few minutes.")
            self.btn_upload.setVisible(False)

    def quarantine_current_file(self):
        if not self.current_file:
            return
            
        success, message = self.wrapper.data_manager.secure_quarantine(self.current_file)
        if success:
            QMessageBox.information(self, "Quarantine", f"Successfully moved to quarantine:\n{self.current_file}")
            self.btn_quarantine.setEnabled(False)
            self.btn_quarantine.setText("Quarantined")
        else:
            QMessageBox.warning(self, "Quarantine Failed", f"Could not quarantine file: {message}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.start_scan(files[0])
