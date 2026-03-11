import os
import random

class DataShredder:
    """
    Implements secure file deletion by overwriting files with random bytes
    before deletion.
    """
    
    @staticmethod
    def shred_file(file_path, passes=3):
        """
        Shreds a file by overwriting it multiple times.
        Returns (success, message).
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        if not os.path.isfile(file_path):
            return False, f"Not a file: {file_path}"
            
        try:
            file_size = os.path.getsize(file_path)
            
            with open(file_path, "ba+", buffering=0) as f:
                for i in range(passes):
                    f.seek(0)
                    # Use different patterns for each pass
                    if i == passes - 1:
                        # Last pass: zero it out
                        f.write(b'\x00' * file_size)
                    else:
                        # Other passes: random bytes
                        f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            os.remove(file_path)
            return True, "File shredded successfully."
            
        except PermissionError:
            return False, "Permission denied. Try running as administrator or checking file permissions."
        except Exception as e:
            return False, f"Error during shredding: {str(e)}"

    @staticmethod
    def shred_directory(dir_path, passes=3, recursive=True):
        """
        Recursively shreds all files in a directory.
        """
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return False, "Invalid directory path."
            
        try:
            for root, dirs, files in os.walk(dir_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    DataShredder.shred_file(file_path, passes)
                
                if recursive:
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
            
            if recursive:
                os.rmdir(dir_path)
                
            return True, "Directory shredded successfully."
        except Exception as e:
            return False, f"Error shredding directory: {str(e)}"
