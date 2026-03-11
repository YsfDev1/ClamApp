import os
import base64

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

class CryptoVault:
    """
    Handles robust file encryption and decryption using cryptography.fernet.
    Uses PBKDF2 for key derivation from a user-provided string.
    """
    
    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """Derives a 32-byte key from a password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @staticmethod
    def encrypt_file(file_path: str, password: str, output_path: str = None):
        """Encrypts a file and saves it with a .vault extension."""
        if not HAS_CRYPTO:
            return False, "cryptography library is not installed. Please install it using 'pip install cryptography'."
        
        if not os.path.exists(file_path):
            return False, "File not found."
        
        if not output_path:
            output_path = file_path + ".vault"
            
        try:
            salt = os.urandom(16)
            key = CryptoVault._derive_key(password, salt)
            fernet = Fernet(key)
            
            with open(file_path, "rb") as f:
                data = f.read()
            
            encrypted_data = fernet.encrypt(data)
            
            with open(output_path, "wb") as f:
                # Store salt first (16 bytes)
                f.write(salt)
                f.write(encrypted_data)
                
            return True, f"File encrypted: {os.path.basename(output_path)}"
        except Exception as e:
            return False, f"Encryption failed: {str(e)}"

    @staticmethod
    def decrypt_file(file_path: str, password: str, output_path: str = None):
        """Decrypts a .vault file."""
        if not HAS_CRYPTO:
            return False, "cryptography library is not installed. Please install it using 'pip install cryptography'."

        if not os.path.exists(file_path):
            return False, "File not found."
            
        try:
            with open(file_path, "rb") as f:
                salt = f.read(16)
                encrypted_data = f.read()
                
            key = CryptoVault._derive_key(password, salt)
            fernet = Fernet(key)
            
            decrypted_data = fernet.decrypt(encrypted_data)
            
            if not output_path:
                if file_path.endswith(".vault"):
                    output_path = file_path[:-6]
                else:
                    output_path = file_path + ".decrypted"
            
            with open(output_path, "wb") as f:
                f.write(decrypted_data)
                
            return True, f"File decrypted: {os.path.basename(output_path)}"
        except Exception as e:
            return False, f"Decryption failed: Incorrect key or corrupted file. ({str(e)})"
