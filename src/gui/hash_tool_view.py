import hashlib
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QFrame, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor


class HashWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha256 = hashlib.sha256()
            with open(self.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
            self.finished.emit({
                "md5": md5.hexdigest(),
                "sha1": sha1.hexdigest(),
                "sha256": sha256.hexdigest(),
                "error": None
            })
        except Exception as e:
            self.finished.emit({"md5": "", "sha1": "", "sha256": "", "error": str(e)})


class HashToolView(QWidget):
    def __init__(self, trans, parent=None):
        super().__init__(parent)
        self.trans = trans
        self.current_hashes = {}
        self.worker = None
        self.is_dark = True
        self.init_ui()
        self.setAcceptDrops(True)

    def apply_theme(self, dark=True):
        self.is_dark = dark
        if dark:
            bg, card, text, border, accent = "#181825", "#313244", "#cdd6f4", "#45475a", "#89b4fa"
        else:
            bg, card, text, border, accent = "#f2f2f5", "#e0e0e8", "#1e1e2e", "#c0c0cc", "#1e66f5"
        self.setAutoFillBackground(True)
        p = self.palette()
        from PyQt6.QtGui import QColor
        p.setColor(self.backgroundRole(), QColor(bg))
        self.setPalette(p)
        self.title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {accent};")
        self.drop_frame.setStyleSheet(f"""
            QFrame {{ background-color: {card}; border: 2px dashed {border};
                border-radius: 12px; padding: 30px; }}
        """)
        self.drop_label.setStyleSheet(f"color: {text}; font-size: 14px;")
        self.btn_browse.setStyleSheet(f"background-color: {border}; color: {text}; padding: 8px 16px; border-radius: 5px;")
        self.file_label.setStyleSheet(f"color: {accent}; font-family: monospace;")
        for row_frame in self.hash_rows:
            row_frame.setStyleSheet(f"background-color: {card}; border-radius: 8px; padding: 8px;")
        for lbl in self.hash_title_labels:
            lbl.setStyleSheet(f"color: {text}; font-weight: bold; min-width: 60px;")
        for box in self.hash_boxes:
            box.setStyleSheet(f"background-color: {'#1e1e2e' if dark else '#ffffff'}; color: {accent}; border: none; font-family: monospace;")
        for btn in self.copy_btns:
            btn.setStyleSheet(f"background-color: {border}; color: {text}; padding: 4px 10px; border-radius: 4px;")
        self.verify_frame.setStyleSheet(f"background-color: {card}; border-radius: 10px; padding: 15px;")
        self.lbl_verify_title.setStyleSheet(f"color: {text}; font-weight: bold; font-size: 14px;")
        self.verify_input.setStyleSheet(f"background-color: {'#1e1e2e' if dark else '#ffffff'}; color: {text}; padding: 8px; border-radius: 5px; font-family: monospace;")
        self.btn_verify.setStyleSheet(f"background-color: {'#89b4fa' if dark else '#1e66f5'}; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 5px;")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title = QLabel(self.trans.get("hash_tool"))
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title)

        # Drop Zone
        self.drop_frame = QFrame()
        self.drop_frame.setStyleSheet("QFrame { background-color: #313244; border: 2px dashed #45475a; border-radius: 12px; padding: 30px; }")
        drop_layout = QVBoxLayout(self.drop_frame)

        self.drop_label = QLabel(self.trans.get("hash_drop_hint"))
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        drop_layout.addWidget(self.drop_label)

        self.btn_browse = QPushButton(self.trans.get("browse"))
        self.btn_browse.setStyleSheet("background-color: #45475a; color: #cdd6f4; padding: 8px 16px; border-radius: 5px;")
        self.btn_browse.clicked.connect(self.browse_file)
        drop_layout.addWidget(self.btn_browse, alignment=Qt.AlignmentFlag.AlignCenter)

        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("color: #89b4fa; font-family: monospace;")
        drop_layout.addWidget(self.file_label)

        layout.addWidget(self.drop_frame)

        # Hash Results
        self.hash_rows = []
        self.hash_title_labels = []
        self.hash_boxes = []
        self.copy_btns = []

        for algo in ["MD5", "SHA-1", "SHA-256"]:
            row_frame = QFrame()
            row_frame.setStyleSheet("background-color: #313244; border-radius: 8px; padding: 8px;")
            row_layout = QHBoxLayout(row_frame)

            lbl_title = QLabel(algo)
            lbl_title.setStyleSheet("color: #cdd6f4; font-weight: bold; min-width: 60px;")
            row_layout.addWidget(lbl_title)

            box = QLineEdit()
            box.setReadOnly(True)
            box.setPlaceholderText("—")
            box.setStyleSheet("background-color: #1e1e2e; color: #89b4fa; border: none; font-family: monospace;")
            row_layout.addWidget(box, 1)

            btn_copy = QPushButton(self.trans.get("copy"))
            btn_copy.setStyleSheet("background-color: #45475a; color: #cdd6f4; padding: 4px 10px; border-radius: 4px;")
            key = algo.lower().replace("-", "")
            btn_copy.clicked.connect(lambda _, b=box: self._copy_hash(b))
            row_layout.addWidget(btn_copy)

            layout.addWidget(row_frame)
            self.hash_rows.append(row_frame)
            self.hash_title_labels.append(lbl_title)
            self.hash_boxes.append(box)
            self.copy_btns.append(btn_copy)

        # Verify Section
        self.verify_frame = QFrame()
        self.verify_frame.setStyleSheet("background-color: #313244; border-radius: 10px; padding: 15px;")
        verify_layout = QVBoxLayout(self.verify_frame)

        self.lbl_verify_title = QLabel(self.trans.get("verify_hash"))
        self.lbl_verify_title.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 14px;")
        verify_layout.addWidget(self.lbl_verify_title)

        verify_row = QHBoxLayout()
        self.verify_input = QLineEdit()
        self.verify_input.setPlaceholderText(self.trans.get("paste_hash_hint"))
        self.verify_input.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 8px; border-radius: 5px; font-family: monospace;")
        verify_row.addWidget(self.verify_input, 1)

        self.btn_verify = QPushButton(self.trans.get("verify"))
        self.btn_verify.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 5px;")
        self.btn_verify.clicked.connect(self.verify_hash)
        verify_row.addWidget(self.btn_verify)
        verify_layout.addLayout(verify_row)

        self.verify_result = QLabel("")
        self.verify_result.setWordWrap(True)
        verify_layout.addWidget(self.verify_result)

        layout.addWidget(self.verify_frame)
        layout.addStretch()

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.trans.get("browse"))
        if path:
            self.calculate_hashes(path)

    def calculate_hashes(self, path):
        if not os.path.isfile(path):
            return
        self.file_label.setText(path)
        self.drop_label.setText(self.trans.get("calculating"))
        for box in self.hash_boxes:
            box.setText("")
        self.worker = HashWorker(path)
        self.worker.finished.connect(self.on_hashes_done)
        self.worker.start()

    def on_hashes_done(self, result):
        self.drop_label.setText(self.trans.get("hash_drop_hint"))
        if result["error"]:
            self.drop_label.setText(f"Error: {result['error']}")
            return
        self.current_hashes = result
        self.hash_boxes[0].setText(result["md5"])
        self.hash_boxes[1].setText(result["sha1"])
        self.hash_boxes[2].setText(result["sha256"])

    def verify_hash(self):
        pasted = self.verify_input.text().strip().lower()
        if not pasted or not self.current_hashes:
            self.verify_result.setText(self.trans.get("no_hash_to_verify"))
            self.verify_result.setStyleSheet("color: #fab387;")
            return

        computed = [
            self.current_hashes.get("md5", ""),
            self.current_hashes.get("sha1", ""),
            self.current_hashes.get("sha256", "")
        ]
        if pasted in computed:
            self.verify_result.setText(f"✅ {self.trans.get('hash_match')}")
            self.verify_result.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        else:
            self.verify_result.setText(f"❌ {self.trans.get('hash_no_match')}")
            self.verify_result.setStyleSheet("color: #f38ba8; font-weight: bold;")

    def _copy_hash(self, box):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(box.text())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.calculate_hashes(files[0])

    def retranslate(self):
        self.title.setText(self.trans.get("hash_tool"))
        self.drop_label.setText(self.trans.get("hash_drop_hint"))
        self.btn_browse.setText(self.trans.get("browse"))
        self.lbl_verify_title.setText(self.trans.get("verify_hash"))
        self.verify_input.setPlaceholderText(self.trans.get("paste_hash_hint"))
        self.btn_verify.setText(self.trans.get("verify"))
        for btn in self.copy_btns:
            btn.setText(self.trans.get("copy"))
