import math
import csv
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

# Import the existing haversine function from intervention_registry if it exists,
# or define it here.
def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# We read from the central CSV for now
DATA_DIR = Path(__file__).resolve().parents[3] / "project" / "data"
INTERVENTIONS_LOG = DATA_DIR / "interventions.csv"

def read_interventions() -> list[dict]:
    if not INTERVENTIONS_LOG.exists():
        return []
    with open(INTERVENTIONS_LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def resolve_intervention(lat: float, lon: float, max_dist_m: float = 500.0) -> Optional[Dict[str, Any]]:
    """
    Finds the nearest intervention from the registry within max_dist_m.
    """
    interventions = read_interventions()
    nearest = None
    min_dist = max_dist_m
    
    for iv in interventions:
        try:
            d = _haversine_m(lat, lon, float(iv["lat"]), float(iv["lon"]))
            if d <= min_dist:
                min_dist = d
                nearest = {**iv, "distance_m": round(d, 1)}
        except (ValueError, KeyError):
            continue
            
    return nearest

def resolve_watershed(lat: float, lon: float) -> Optional[str]:
    """
    In a full implementation, this would do a point-in-polygon query against a 
    PostGIS or similar geospatial database containing all micro-watersheds.
    For this MVP, we return a mock ID based on coordinates.
    The actual boundaries are fetched by watershed_delineation.py on-the-fly via PySheds.
    """
    # Simply generate a deterministic ID based on the rounded grid block
    lat_block = int(lat * 10)
    lon_block = int(lon * 10)
    return f"WS-{lat_block}-{lon_block}"

def resolve_satellite_time(photo_date_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Given a photo capture date, determine the optimal T1 and T2 satellite dates.
    For MVP, T2 is the photo date (or latest available before it), and T1 is 1 year prior.
    """
    if not photo_date_str:
        return None, None
        
    try:
        # Expecting ISO format like 2026-08-20T10:42:00
        photo_date = datetime.fromisoformat(photo_date_str.replace("Z", "+00:00"))
        
        # Format as YYYY-MM-DD for Sentinel-2 search
        t2 = photo_date.strftime("%Y-%m-%d")
        
        # T1 is one year prior to T2
        # Handle leap year edge cases
        try:
            t1_date = photo_date.replace(year=photo_date.year - 1)
        except ValueError:
            # Leap day
            t1_date = photo_date.replace(year=photo_date.year - 1, day=28)
            
        t1 = t1_date.strftime("%Y-%m-%d")
        return t1, t2
    except Exception as e:
        print(f"Error resolving satellite time: {e}")
        return None, None
