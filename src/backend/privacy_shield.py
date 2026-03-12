try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
import os

class PrivacyShield:
    """
    Inspects and sanitizes image files by removing metadata (EXIF).
    """
    
    @staticmethod
    def get_metadata(image_path):
        """
        Extracts metadata from an image and returns it as a dictionary.
        """
        if not HAS_PILLOW:
            return {"Error": "python3-pil/Pillow is not installed. Please install it using 'pip install Pillow'."}
        
        metadata = {}
        if not os.path.exists(image_path):
            return {"Error": "File not found."}
            
        try:
            image = Image.open(image_path)
            info = image.getexif()
            if not info:
                return {"Message": "No EXIF metadata found."}
                
            for tag_id, value in info.items():
                tag = TAGS.get(tag_id, tag_id)
                # Convert some values to strings if they aren't JSON serializable or readable
                if isinstance(value, bytes):
                    value = value.decode(errors='replace')
                metadata[tag] = str(value)
                
            return metadata
        except Exception as e:
            return {"Error": f"Could not read metadata: {str(e)}"}

    @staticmethod
    def sanitize_image(image_path, output_path=None):
        """
        Creates a copy of the image without any metadata.
        Preserves image quality as much as possible.
        """
        if not HAS_PILLOW:
            return False, "python3-pil/Pillow is not installed. Please install it using 'pip install Pillow'."
            
        if not os.path.exists(image_path):
            return False, "File not found."
            
        try:
            image = Image.open(image_path)
            
            # Remove EXIF by simply saving without it
            data = list(image.getdata())
            image_without_exif = Image.new(image.mode, image.size)
            image_without_exif.putdata(data)
            
            if not output_path:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_sanitized{ext}"
            
            # Save without metadata
            image_without_exif.save(output_path, quality=95, optimize=True)
            
            return True, f"Image sanitized: {os.path.basename(output_path)}"
        except Exception as e:
            return False, f"Sanitization failed: {str(e)}"
