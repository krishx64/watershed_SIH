import io
from PIL import Image, ExifTags
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

_GPS_TAG_ID = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), 34853)
_DATETIME_TAG_ID = next((k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"), 36867)

def _dms_to_decimal(dms, ref: str) -> float:
    """EXIF GPS stores (degrees, minutes, seconds) -- convert to signed decimal degrees."""
    degrees, minutes, seconds = (float(v) for v in dms)
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal

def extract_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts GPS, timestamp, and other metadata from an image's EXIF data.
    """
    result = {
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "gps_accuracy_m": None,
        "captured_at": None,
        "metadata_status": "INVALID",
        "make": None,
        "model": None
    }
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        
        if not exif:
            return result
            
        # Get basic tags
        result["make"] = exif.get(271) # Make
        result["model"] = exif.get(272) # Model
        
        # DateTimeOriginal (36867) is typically in EXIF IFD, not main IFD
        # but let's try both
        dt_str = exif.get(_DATETIME_TAG_ID)
        
        # Try getting EXIF IFD
        exif_ifd = exif.get_ifd(34665)
        if exif_ifd and not dt_str:
            dt_str = exif_ifd.get(_DATETIME_TAG_ID)
            
        if dt_str:
            try:
                # EXIF format is typically "YYYY:MM:DD HH:MM:SS"
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                result["captured_at"] = dt.isoformat()
            except ValueError:
                pass

        # GPS Info
        gps_ifd = exif.get_ifd(_GPS_TAG_ID)
        if gps_ifd:
            try:
                lat = _dms_to_decimal(gps_ifd[2], gps_ifd[1])  # GPSLatitude, GPSLatitudeRef
                lon = _dms_to_decimal(gps_ifd[4], gps_ifd[3])  # GPSLongitude, GPSLongitudeRef
                result["latitude"] = round(lat, 6)
                result["longitude"] = round(lon, 6)
                
                # Altitude
                if 6 in gps_ifd and 5 in gps_ifd:
                    alt = float(gps_ifd[6])
                    ref = int(gps_ifd[5])
                    result["altitude"] = -alt if ref == 1 else alt
                    
                # HPositioningError (GPS accuracy)
                if 31 in gps_ifd:
                    result["gps_accuracy_m"] = float(gps_ifd[31])
            except Exception as e:
                print(f"Error parsing GPS data: {e}")
        
        # Determine metadata status
        if result["latitude"] is not None and result["longitude"] is not None:
            if result["captured_at"] is not None:
                result["metadata_status"] = "VALID"
            else:
                result["metadata_status"] = "PARTIAL" # Missing time
        elif result["captured_at"] is not None:
            result["metadata_status"] = "MISSING_GPS"
            
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        
    return result
