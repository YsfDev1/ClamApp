"""
test_network_monitor.py — Unit tests for NetworkMonitorThread.

psutil calls are fully mocked so the test suite runs without root
privileges or a live network interface.
"""
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── Helpers / fixtures ────────────────────────────────────────────────────
def _make_conn(proto_type=1, pid=1234, lhost="127.0.0.1", lport=8080,
               rhost="8.8.8.8", rport=443, status="ESTABLISHED"):
    """Build a mock psutil connection named-tuple."""
    conn = MagicMock()
    conn.type = proto_type          # 1 = SOCK_STREAM (TCP)
    conn.pid = pid
    conn.laddr = MagicMock(ip=lhost, port=lport)
    conn.raddr = MagicMock(ip=rhost, port=rport)
    conn.status = status
    return conn


# ── Tests ─────────────────────────────────────────────────────────────────
class TestNetworkMonitorThreadCollect(unittest.TestCase):
    """Test the _collect() helper that runs inside the worker thread."""

    def _get_thread(self):
        from gui.network_monitor_thread import NetworkMonitorThread
        return NetworkMonitorThread(interval=0.1)

    @patch("gui.network_monitor_thread.psutil")
    def test_collect_returns_list_of_dicts(self, mock_psutil):
        mock_psutil.net_connections.return_value = [_make_conn()]
        proc = MagicMock()
        proc.name.return_value = "firefox"
        mock_psutil.Process.return_value = proc

        thread = self._get_thread()
        result = thread._collect()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertIn("proto", entry)
        self.assertIn("pid", entry)
        self.assertIn("name", entry)
        self.assertIn("laddr", entry)
        self.assertIn("raddr", entry)
        self.assertIn("status", entry)

    @patch("gui.network_monitor_thread.psutil")
    def test_tcp_proto_label(self, mock_psutil):
        mock_psutil.net_connections.return_value = [_make_conn(proto_type=1)]
        mock_psutil.Process.return_value.name.return_value = "sshd"

        thread = self._get_thread()
        result = thread._collect()
        self.assertEqual(result[0]["proto"], "TCP")

    @patch("gui.network_monitor_thread.psutil")
    def test_udp_proto_label(self, mock_psutil):
        mock_psutil.net_connections.return_value = [_make_conn(proto_type=2)]
        mock_psutil.Process.return_value.name.return_value = "avahi"

        thread = self._get_thread()
        result = thread._collect()
        self.assertEqual(result[0]["proto"], "UDP")

    @patch("gui.network_monitor_thread.psutil")
    def test_unknown_pid_name_is_dash(self, mock_psutil):
        """When Process() raises NoSuchProcess, name should be '—'."""
        conn = _make_conn(pid=9999)
        mock_psutil.net_connections.return_value = [conn]
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        mock_psutil.Process.side_effect = Exception("gone")

        thread = self._get_thread()
        result = thread._collect()
        self.assertEqual(result[0]["name"], "—")

    @patch("gui.network_monitor_thread.psutil")
    def test_no_pid_returns_dash(self, mock_psutil):
        """Connections without a PID should show '—'."""
        conn = _make_conn(pid=None)
        mock_psutil.net_connections.return_value = [conn]

        thread = self._get_thread()
        result = thread._collect()
        self.assertEqual(result[0]["pid"], "—")

    @patch("gui.network_monitor_thread.psutil")
    def test_empty_connection_list(self, mock_psutil):
        mock_psutil.net_connections.return_value = []
        thread = self._get_thread()
        self.assertEqual(thread._collect(), [])

    @patch("gui.network_monitor_thread.psutil")
    def test_malformed_entry_skipped(self, mock_psutil):
        """An exception on a single entry must not abort the whole list."""
        good = _make_conn()
        bad = MagicMock()
        bad.type = "BREAK_ME"    # accessing .pid will raise
        bad.pid = MagicMock(side_effect=RuntimeError("oops"))
        mock_psutil.net_connections.return_value = [bad, good]
        mock_psutil.Process.return_value.name.return_value = "ok"

        thread = self._get_thread()
        result = thread._collect()
        # At least the good entry should be present
        self.assertGreaterEqual(len(result), 1)


class TestNetworkMonitorThreadLifecycle(unittest.TestCase):
    """Test start/stop lifecycle without a Qt event loop."""

    @patch("gui.network_monitor_thread.psutil")
    def test_stop_halts_thread(self, mock_psutil):
        """Thread should stop within 2 s after stop() is called."""
        mock_psutil.net_connections.return_value = []
        mock_psutil.HAS_PSUTIL = True

        from gui.network_monitor_thread import NetworkMonitorThread
        thread = NetworkMonitorThread(interval=0.3)
        thread.start()
        time.sleep(0.5)   # Let it run one cycle
        thread.stop()
        self.assertFalse(thread.isRunning(), "Thread should have stopped")


if __name__ == "__main__":
    unittest.main()
