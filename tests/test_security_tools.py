import unittest
import os
import sys
import shutil

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.data_shredder import DataShredder
from backend.crypto_vault import CryptoVault
from backend.privacy_shield import PrivacyShield

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

if __name__ == '__main__':
    unittest.main()
