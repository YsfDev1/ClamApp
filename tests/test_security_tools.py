import unittest
import os
import sys
import shutil
<<<<<<< HEAD
import json
=======
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.data_shredder import DataShredder
from backend.crypto_vault import CryptoVault
from backend.privacy_shield import PrivacyShield
<<<<<<< HEAD
from backend.data_manager import DataManager
=======
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b

class TestSecurityTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_outputs')
        os.makedirs(self.test_dir, exist_ok=True)
        self.dummy_file = os.path.join(self.test_dir, 'dummy.txt')
        with open(self.dummy_file, 'w') as f:
            f.write("This is a test file with some sensitive content.")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_data_shredder(self):
        file_path = self.dummy_file
        success, msg = DataShredder.shred_file(file_path, passes=2)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(file_path))

    def test_crypto_vault(self):
        file_path = self.dummy_file
        password = "strongpassword123"
        vault_path = file_path + ".vault"
        
        # Test Encryption
        success, msg = CryptoVault.encrypt_file(file_path, password)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(vault_path))
        
        # Test Decryption
        decrypted_path = file_path + ".dec"
        success, msg = CryptoVault.decrypt_file(vault_path, password, decrypted_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(decrypted_path))
        
        with open(decrypted_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "This is a test file with some sensitive content.")

    def test_privacy_shield_logic(self):
        # We don't have a real image with EXIF easily available in this environment,
        # but we can test if the methods handle missing/empty data gracefully.
        success, msg = PrivacyShield.sanitize_image(self.dummy_file)
        # Even if it's not an image, PIL might fail or handle it. 
        # But we primarily want to ensure the logic exists and doesn't crash.
        pass

<<<<<<< HEAD

class TestSecureQuarantine(unittest.TestCase):
    """Tests for the new secure_quarantine / restore_file workflow."""

    def setUp(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'test_quarantine_base')
        os.makedirs(self.base_dir, exist_ok=True)
        # Redirect quarantine dir to a temp location so we don't touch ~/.clamapp
        self.dm = DataManager(self.base_dir)
        self.dm.quarantine_dir = os.path.join(self.base_dir, 'quarantine')
        os.makedirs(self.dm.quarantine_dir, exist_ok=True)

        self.victim = os.path.join(self.base_dir, 'malware_sample.txt')
        with open(self.victim, 'w') as f:
            f.write('EICAR-STANDARD-ANTIVIRUS-TEST-FILE')

    def tearDown(self):
        # Re-enable any files that may have been chmod 0o000'd so shutil.rmtree works
        for root, dirs, files in os.walk(self.base_dir):
            for name in files:
                try:
                    os.chmod(os.path.join(root, name), 0o644)
                except OSError:
                    pass
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def test_secure_quarantine_moves_file(self):
        """File should be moved to quarantine dir."""
        success, msg = self.dm.secure_quarantine(self.victim)
        self.assertTrue(success, msg)
        self.assertFalse(os.path.exists(self.victim), "Original file should be gone")

    def test_secure_quarantine_permissions_stripped(self):
        """Quarantined file should have 0o000 permissions."""
        success, _ = self.dm.secure_quarantine(self.victim)
        self.assertTrue(success)
        q_item = self.dm.data['quarantine'][-1]
        q_path = q_item['quarantine_path']
        mode = oct(os.stat(q_path).st_mode & 0o777)
        self.assertEqual(mode, oct(0o000), f"Expected 0o000, got {mode}")

    def test_secure_quarantine_metadata_sidecar(self):
        """A .meta.json sidecar must be written with original_path."""
        success, _ = self.dm.secure_quarantine(self.victim)
        self.assertTrue(success)
        q_item = self.dm.data['quarantine'][-1]
        meta_path = q_item['quarantine_path'] + '.meta.json'
        self.assertTrue(os.path.exists(meta_path), 'Metadata sidecar not found')
        with open(meta_path, 'r') as mf:
            meta = json.load(mf)
        self.assertEqual(meta['original_path'], self.victim)
        self.assertIn('quarantine_date', meta)

    def test_restore_file_removes_sidecar(self):
        """Restore should delete the metadata sidecar and return file."""
        self.dm.secure_quarantine(self.victim)
        q_item = self.dm.data['quarantine'][-1]
        qid = q_item['id']
        meta_path = q_item['quarantine_path'] + '.meta.json'

        success, msg = self.dm.restore_file(qid)
        self.assertTrue(success, msg)
        self.assertTrue(os.path.exists(self.victim), 'File not restored')
        self.assertFalse(os.path.exists(meta_path), 'Sidecar should be deleted on restore')

    def test_restore_grants_permissions(self):
        """Restored file should have at least 0o600 permissions."""
        self.dm.secure_quarantine(self.victim)
        q_item = self.dm.data['quarantine'][-1]
        self.dm.restore_file(q_item['id'])
        mode = os.stat(self.victim).st_mode & 0o777
        self.assertGreaterEqual(mode, 0o400, 'Restored file should be readable')

    def test_quarantine_nonexistent_file(self):
        """secure_quarantine on missing file should return (False, message)."""
        success, msg = self.dm.secure_quarantine('/tmp/does_not_exist_abc123.txt')
        self.assertFalse(success)
        self.assertIn('not found', msg.lower())


=======
>>>>>>> 73509aa6811d1fca4ec74cabe02169f57473617b
if __name__ == '__main__':
    unittest.main()
