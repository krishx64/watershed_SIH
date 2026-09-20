import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from storage.database import save_geo_photo, get_geo_photo
from storage.photo_store import save_photo
from services.metadata_service import extract_metadata
from services.spatial_resolver import resolve_watershed, resolve_intervention

def ingest_photo(filename: str, content: bytes, source: str = "web_upload") -> str:
    """
    Ingests an uploaded photo, extracts metadata, saves it, and returns the photo_id.
    """
    photo_id = f"PHOTO-{uuid.uuid4().hex[:8].upper()}"
    
    # Save files
    file_uri, thumb_uri, sha256 = save_photo(photo_id, filename, content)
    
    # Extract metadata
    meta = extract_metadata(content)
    
    # Coordinate resolution if GPS is present
    watershed_id = None
    intervention_id = None
    
    if meta["latitude"] is not None and meta["longitude"] is not None:
        watershed_id = resolve_watershed(meta["latitude"], meta["longitude"])
        nearest = resolve_intervention(meta["latitude"], meta["longitude"])
        if nearest:
            intervention_id = nearest["id"] # Assuming 'id' is in interventions.csv
            
    # Prepare record
    record = {
        "photo_id": photo_id,
        "file_uri": file_uri,
        "thumbnail_uri": thumb_uri,
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "altitude": meta["altitude"],
        "gps_accuracy_m": meta["gps_accuracy_m"],
        "captured_at": meta["captured_at"],
        "source": source,
        "watershed_id": watershed_id,
        "intervention_id": intervention_id,
        "metadata_status": meta["metadata_status"],
        "analysis_status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256
    }
    
    # Save to DB
    save_geo_photo(record)
    
    return photo_id

def resolve_context(photo_id: str) -> Dict[str, Any]:
    """
    Resolves the full context for a photo before analysis begins.
    """
    photo = get_geo_photo(photo_id)
    if not photo:
        raise ValueError(f"Photo {photo_id} not found")
        
    if photo["latitude"] is None or photo["longitude"] is None:
        raise ValueError("Cannot resolve context without GPS coordinates")
        
    # Re-run resolution if not present
    if not photo["watershed_id"]:
        photo["watershed_id"] = resolve_watershed(photo["latitude"], photo["longitude"])
    
    nearest_iv = resolve_intervention(photo["latitude"], photo["longitude"])
    if nearest_iv:
        photo["intervention_id"] = nearest_iv.get("id")
        
    # Save updates if any
    save_geo_photo(photo)
    
    from services.spatial_resolver import resolve_satellite_time
    t1, t2 = resolve_satellite_time(photo["captured_at"])
    
    return {
        "photo_id": photo_id,
        "watershed_id": photo["watershed_id"],
        "intervention": nearest_iv,
        "satellite": {
            "t1": t1,
            "t2": t2
        },
        "latitude": photo["latitude"],
        "longitude": photo["longitude"]
    }
