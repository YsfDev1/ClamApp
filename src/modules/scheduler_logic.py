from PyQt6.QtCore import QObject, QTimer, QDateTime, pyqtSignal

class ScheduleLogic(QObject):
    trigger_scan = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_schedule)
        self.last_fired_date = None

    def start(self):
        self.timer.start(60000) # Check every minute

    def check_schedule(self):
        enabled = self.settings_manager.get("daily_scan_enabled", False)
        if not enabled:
            return

        target_time = self.settings_manager.get("scan_time", "03:00")
        now = QDateTime.currentDateTime()
        current_time = now.toString("HH:mm")
        current_date = now.date().toString()

        if current_time == target_time:
            if self.last_fired_date != current_date:
                self.last_fired_date = current_date
                self.trigger_scan.emit()
