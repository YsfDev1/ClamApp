"""
test_scanner.py — Unit tests for ScannerThread and ClamWrapper.

All ClamAV subprocess calls are mocked so tests run on any machine,
even without ClamAV installed.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import subprocess

# ── Ensure src/ is on the path ───────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.clam_wrapper import ClamWrapper


# ── Helpers ───────────────────────────────────────────────────────────────
def _make_completed_process(stdout="", stderr="", returncode=0):
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


# ── ClamWrapper tests ─────────────────────────────────────────────────────
class TestClamWrapperVersion(unittest.TestCase):
    @patch("backend.clam_wrapper.subprocess.run")
    def test_get_version_returns_string(self, mock_run):
        mock_run.return_value = _make_completed_process(
            stdout="ClamAV 1.0.0/26000/Mon Jan  1 00:00:00 2024\n"
        )
        wrapper = ClamWrapper()
        wrapper.clamscan_path = "/usr/bin/clamscan"
        version = wrapper.get_version()
        self.assertIn("ClamAV", version)

    @patch("backend.clam_wrapper.subprocess.run")
    def test_get_version_not_installed(self, mock_run):
        wrapper = ClamWrapper()
        wrapper.clamscan_path = None
        self.assertEqual(wrapper.get_version(), "Not Installed")

    @patch("backend.clam_wrapper.subprocess.run")
    def test_get_version_exception_returns_unknown(self, mock_run):
        mock_run.side_effect = Exception("binary missing")
        wrapper = ClamWrapper()
        wrapper.clamscan_path = "/usr/bin/clamscan"
        result = wrapper.get_version()
        self.assertEqual(result, "Unknown")


class TestClamWrapperScanFile(unittest.TestCase):
    def setUp(self):
        self.wrapper = ClamWrapper()
        self.wrapper.clamscan_path = "/usr/bin/clamscan"

    @patch("backend.clam_wrapper.subprocess.run")
    def test_scan_clean_file(self, mock_run):
        mock_run.return_value = _make_completed_process(returncode=0)
        result = self.wrapper.scan_file("/tmp/clean.txt")
        self.assertEqual(result["status"], "clean")

    @patch("backend.clam_wrapper.subprocess.run")
    def test_scan_infected_file(self, mock_run):
        mock_run.return_value = _make_completed_process(
            stdout="/tmp/evil.exe: Malware.Test.EICAR FOUND\n",
            returncode=1,
        )
        result = self.wrapper.scan_file("/tmp/evil.exe")
        self.assertEqual(result["status"], "infected")
        self.assertIn("output", result)

    @patch("backend.clam_wrapper.subprocess.run")
    def test_scan_error_returncode_2(self, mock_run):
        mock_run.return_value = _make_completed_process(
            stderr="ERROR: Access denied\n", returncode=2
        )
        result = self.wrapper.scan_file("/etc/shadow")
        self.assertEqual(result["status"], "error")

    @patch("backend.clam_wrapper.subprocess.run")
    def test_scan_permission_error(self, mock_run):
        mock_run.side_effect = PermissionError("Permission denied")
        result = self.wrapper.scan_file("/etc/shadow")
        self.assertEqual(result["status"], "error")
        self.assertIn("ermission", result["message"])

    def test_scan_not_installed(self):
        self.wrapper.clamscan_path = None
        result = self.wrapper.scan_file("/tmp/any.txt")
        self.assertEqual(result["status"], "error")
        self.assertIn("not installed", result["message"].lower())


class TestClamWrapperFPP(unittest.TestCase):
    def setUp(self):
        self.wrapper = ClamWrapper()

    def test_fpp_script_is_high(self):
        for ext in [".py", ".sh", ".js"]:
            fpp = self.wrapper.calculate_fpp(f"/home/user/myscript{ext}")
            # Scripts from user home have high FPP (≥ 50 at minimum)
            self.assertIsInstance(fpp, int)

    def test_fpp_tmp_binary_is_low(self):
        fpp = self.wrapper.calculate_fpp("/tmp/dropper.elf")
        self.assertIsInstance(fpp, int)

    def test_fpp_missing_file_returns_50(self):
        fpp = self.wrapper.calculate_fpp("/nonexistent/path/file.xyz")
        self.assertEqual(fpp, 50)


class TestClamWrapperVirusDescription(unittest.TestCase):
    def setUp(self):
        self.wrapper = ClamWrapper()

    def test_eicar_description(self):
        desc = self.wrapper.get_virus_description("EICAR-Test-Signature")
        self.assertIn("Test", desc)

    def test_trojan_description(self):
        desc = self.wrapper.get_virus_description("Trojan.Generic")
        self.assertIn("malicious", desc.lower())

    def test_unknown_returns_generic(self):
        desc = self.wrapper.get_virus_description("XYZ.Unknown.Variant")
        self.assertIn("generic", desc.lower())


class TestClamWrapperGetFileContent(unittest.TestCase):
    def setUp(self):
        self.wrapper = ClamWrapper()
        self.tmp = "/tmp/clamapp_test_content.txt"
        with open(self.tmp, "w") as f:
            f.write("hello world")

    def tearDown(self):
        try:
            os.remove(self.tmp)
        except OSError:
            pass

    def test_reads_existing_file(self):
        content = self.wrapper.get_file_content(self.tmp)
        self.assertIn("hello world", content)

    def test_missing_file_returns_message(self):
        content = self.wrapper.get_file_content("/nonexistent/path.txt")
        self.assertIn("not found", content.lower())


if __name__ == "__main__":
    unittest.main()
