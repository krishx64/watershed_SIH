import os
import shutil
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import io

PHOTO_DIR = Path(__file__).resolve().parents[2] / "data" / "photos"
THUMBNAIL_DIR = PHOTO_DIR / "thumbnails"

PHOTO_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

def generate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def save_photo(photo_id: str, filename: str, content: bytes) -> Tuple[str, str, str]:
    """
    Saves the original photo and generates a thumbnail.
    Returns (file_uri, thumbnail_uri, sha256_hash).
    """
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    if ext not in ["jpg", "jpeg", "png", "heic"]:
        ext = "jpg"
        
    photo_filename = f"{photo_id}.{ext}"
    thumb_filename = f"{photo_id}_thumb.{ext}"
    
    photo_path = PHOTO_DIR / photo_filename
    thumb_path = THUMBNAIL_DIR / thumb_filename
    
    # Save original
    with open(photo_path, "wb") as f:
        f.write(content)
        
    # Generate hash
    file_hash = generate_file_hash(content)
    
    # Generate thumbnail
    try:
        img = Image.open(io.BytesIO(content))
        # Ensure it's in a compatible mode for thumbnail generation
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail((300, 300))
        img.save(thumb_path, format="JPEG" if ext in ["jpg", "jpeg"] else "PNG")
    except Exception as e:
        print(f"Error generating thumbnail for {photo_id}: {e}")
        # Fallback to copy original if thumbnail fails
        shutil.copy2(photo_path, thumb_path)

    # Return local URIs that can be served via static file serving
    file_uri = f"/data/photos/{photo_filename}"
    thumb_uri = f"/data/photos/thumbnails/{thumb_filename}"
    
    return file_uri, thumb_uri, file_hash

def get_photo_path(photo_id: str) -> Optional[Path]:
    """Finds the photo file by ID"""
    for p in PHOTO_DIR.glob(f"{photo_id}.*"):
        if p.is_file():
            return p
    return None
