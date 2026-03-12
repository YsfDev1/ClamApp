import os
import threading
try:
    import pyudev
    HAS_PYUDEV = True
except ImportError:
    HAS_PYUDEV = False

class USBGuardianLogic:
    """
    Monitors USB device insertion and identifies mount points.
    """
    def __init__(self, callback=None):
        self.callback = callback
        self.observer = None
        self.running = False

    def start_monitoring(self):
        if not HAS_PYUDEV:
            print("USB Guardian: pyudev not installed.")
            return

        self.running = True
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='block', device_type='partition')

        def handle_event(action, device):
            if action == 'add':
                # Wait a bit for the system to auto-mount
                import time
                time.sleep(2)
                mount_point = self._get_mount_point(device.device_node)
                if mount_point and self.callback:
                    self.callback(mount_point)

        self.observer = pyudev.MonitorObserver(monitor, handle_event)
        self.observer.start()
        print("USB Guardian: Monitoring started...")

    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.running = False
            print("USB Guardian: Monitoring stopped.")

    def _get_mount_point(self, device_node):
        """
        Parses /proc/mounts to find where the device is mounted.
        """
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if parts[0] == device_node:
                        return parts[1]
        except Exception as e:
            print(f"USB Guardian: Error getting mount point: {e}")
        return None
