import hashlib
import requests
import os

class VTService:
    """
    Service for interacting with VirusTotal API v3.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://www.virustotal.com/api/v3"

    def set_api_key(self, api_key):
        self.api_key = api_key

    def get_file_hash(self, file_path):
        """Calculates SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return None

    def get_report(self, file_hash):
        """Retrieves a file report from VirusTotal."""
        if not self.api_key:
            return {"error": "API Key not set"}
        
        headers = {"x-apikey": self.api_key}
        url = f"{self.base_url}/files/{file_hash}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"not_found": True}
            else:
                return {"error": f"API Error: {response.status_code}", "detail": response.text}
        except Exception as e:
            return {"error": str(e)}

    def upload_file(self, file_path):
        """Uploads a file to VirusTotal for analysis."""
        if not self.api_key:
            return {"error": "API Key not set"}

        headers = {"x-apikey": self.api_key}
        url = f"{self.base_url}/files"
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                response = requests.post(url, headers=headers, files=files, timeout=30)
                
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Upload Error: {response.status_code}", "detail": response.text}
        except Exception as e:
            return {"error": str(e)}
