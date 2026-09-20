"""
data_adapter.py — Unified Government Data Adapter with AWS S3 Fallback.
Implements the PS-26015 Ingestion Seam:
1. Bhoonidhi Resourcesat-2/2A LISS-3 reader (via native /vsizip/ without unzipping).
2. Live Bhuvan LULC statistics API client (curl_aoi.php) with Redis/in-memory cache.
3. Automated AWS S3 fallback (Sentinel-2 STAC and Copernicus GLO-30 DEM).
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import ssl
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import numpy as np
import rasterio
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.windows import from_bounds
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Load environment variables
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

import uuid
from config import (
    AOI_BBOX, DATA_RAW, DATA_PROCESSED, OUTPUTS_DIR, atomic_raster_write
)
from cache_manager import cache
import mongo_raster_cache as mrc
from bhoonidhi_client import BhoonidhiClient

BHOONIDHI_DIR = PROJECT_ROOT / "bhoonidhi_data"
BHOONIDHI_DIR.mkdir(parents=True, exist_ok=True)

# Bhuvan LULC code mapping to human-readable names
BHUVAN_CODE_MAP = {
    "l01": "Builtup, Urban",
    "l02": "Builtup, Rural",
    "l03": "Builtup, Mining",
    "l04": "Agriculture, Cropland",
    "l05": "Agriculture, Plantation",
    "l06": "Agriculture, Fallow",
    "l08": "Forest, Evergreen",
    "l09": "Forest, Deciduous",
    "l11": "Forest, Scrub",
    "l14": "Wasteland, Salt Affected",
    "l16": "Wasteland, Scrubland",
    "l18": "Barren Rocky",
    "l22": "River / Stream / Canal",
    "l23": "Reservoir / Lake / Pond",
}


# ============================================================================
# 1. Bhuvan REST API Client
# ============================================================================

def get_bhuvan_token() -> str:
    """Read Bhuvan LULC token from .env."""
    return os.environ.get("BHUVAN_TOKEN_LULC", "").strip()


def fetch_bhuvan_aoi_stats(bbox: tuple = AOI_BBOX) -> Dict[str, Any]:
    """
    Query Bhuvan 50k LULC statistics for bbox using curl_aoi.php.
    Returns parsed class areas in sq km and percentage distribution.
    Caches result in Redis / in-memory cache.
    """
    cache_key = f"bhuvan_stats_{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}"
    cached = cache.get_json(cache_key)
    if cached:
        print(f"--> [Cache] ({cache.backend_name.upper()}) Cache HIT for Bhuvan AOI stats [{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]", flush=True)
        return cached

    token = get_bhuvan_token()
    if not token:
        print("--> [Bhuvan API] No BHUVAN_TOKEN_LULC in .env. Using baseline reference fallback.", flush=True)
        return _fallback_bhuvan_stats("Token missing in .env")

    # Construct WKT Polygon from bbox: (minx, miny, maxx, maxy)
    minx, miny, maxx, maxy = bbox
    wkt = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
    url = f"https://bhuvan-app1.nrsc.gov.in/api/lulc/curl_aoi.php?geom={urllib.parse.quote(wkt)}&token={token}"

    print(f"--> [Bhuvan API] Querying live 50k LULC statistics for AOI [{minx:.4f}, {miny:.4f}, {maxx:.4f}, {maxy:.4f}]...", flush=True)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (WatershedSignal/1.0)",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data or not isinstance(data, list) or len(data) == 0:
                print("--> [Bhuvan API] Server returned empty payload. Using baseline reference.", flush=True)
                return _fallback_bhuvan_stats("Empty response from Bhuvan")
            
            record = data[0]
            state = record.get("State", "IN")
            classes = {}
            total_sqkm = 0.0

            for k, val in record.items():
                clean_k = k.strip("'\"")
                if clean_k in BHUVAN_CODE_MAP:
                    area = float(val)
                    total_sqkm += area
                    classes[BHUVAN_CODE_MAP[clean_k]] = {
                        "code": clean_k,
                        "sqkm": area,
                    }

            for name, cinfo in classes.items():
                cinfo["pct"] = round((cinfo["sqkm"] / total_sqkm) * 100, 2) if total_sqkm > 0 else 0

            print(f"--> [Bhuvan API] SUCCESS! Received {len(classes)} official land-cover classes (State: {state}, Total Area: {total_sqkm:.2f} km²)", flush=True)
            for cname, cinfo in classes.items():
                print(f"    • {cname:25s} : {cinfo['sqkm']:6.2f} km² ({cinfo['pct']:5.2f}%)", flush=True)

            result = {
                "status": "success",
                "source": "ISRO Bhuvan 50k LULC (Live API)",
                "state": state,
                "total_sqkm": round(total_sqkm, 2),
                "classes": classes,
                "token_valid": True,
            }
            cache.set_json(cache_key, result, ttl=86400)
            print(f"--> [Cache] Saved Bhuvan stats to {cache.backend_name.upper()} cache (TTL: 24h)", flush=True)
            return result
    except Exception as e:
        print(f"--> [Bhuvan API] Request failed: {e}. Gracefully activating baseline fallback.", flush=True)
        return _fallback_bhuvan_stats(str(e))


def _fallback_bhuvan_stats(reason: str) -> Dict[str, Any]:
    """Baseline fallback when Bhuvan API is unavailable or expired."""
    return {
        "status": "fallback",
        "source": "ESA WorldCover / Kadwanchi Historical Reference",
        "reason": reason,
        "token_valid": False,
        "total_sqkm": 81.23,
        "classes": {
            "Agriculture, Cropland": {"code": "l04", "sqkm": 33.81, "pct": 41.62},
            "Agriculture, Fallow": {"code": "l06", "sqkm": 28.41, "pct": 34.97},
            "Barren Rocky": {"code": "l18", "sqkm": 11.52, "pct": 14.18},
            "Wasteland, Scrubland": {"code": "l16", "sqkm": 4.44, "pct": 5.47},
            "Reservoir / Lake / Pond": {"code": "l23", "sqkm": 2.96, "pct": 3.64},
            "Builtup, Rural": {"code": "l02", "sqkm": 0.09, "pct": 0.11},
        }
    }


# ============================================================================
# 2. Bhoonidhi Resourcesat-2/2A LISS-3 Optical Ingestion (Zero-Extraction)
# ============================================================================

import re
from datetime import datetime

def parse_bhoonidhi_date(stem: str):
    """Extract date from Bhoonidhi scene stem like RA327DEC2025..."""
    m = re.search(r'(\d{2})([A-Z]{3})(\d{4})', stem)
    if m:
        d, mon, y = m.groups()
        try:
            return datetime.strptime(f"{d}{mon}{y}", "%d%b%Y").date()
        except Exception:
            pass
    return None


def find_matching_bhoonidhi_scenes(bbox: tuple = AOI_BBOX) -> list:
    """
    Search Bhoonidhi ZIP archives in bhoonidhi_data/ that fully cover the requested bbox
    with 100% non-zero valid pixels.
    Returns list of tuples: (date_obj, zpath, stem) sorted by date ascending.
    """
    if not BHOONIDHI_DIR.exists():
        return []

    zips = list(BHOONIDHI_DIR.glob("*.zip"))
    if not zips:
        return []

    matches = []
    for zpath in zips:
        stem = zpath.stem
        vsi_band2 = f"/vsizip/{zpath.resolve().as_posix()}/{stem}/BAND2.tif"
        try:
            with rasterio.open(vsi_band2) as src:
                minx, miny, maxx, maxy = transform_bounds("EPSG:4326", src.crs, *bbox)
                win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
                if win.col_off >= 0 and win.row_off >= 0 and \
                   (win.col_off + win.width) <= src.width and \
                   (win.row_off + win.height) <= src.height:
                    sample = src.read(1, window=win)
                    if np.count_nonzero(sample) == sample.size:
                        dt = parse_bhoonidhi_date(stem) or datetime.min.date()
                        matches.append((dt, zpath, stem))
        except Exception:
            continue

    matches.sort(key=lambda x: x[0])
    return matches


def find_best_bhoonidhi_scene(
    bbox: tuple = AOI_BBOX,
    date_tag: str = "T2",
    target_date: Optional[str] = None,
) -> Optional[Tuple[Any, Path, str]]:
    """
    Find best Bhoonidhi scene covering bbox:
      - If target_date specified: picks scene closest in date to target_date.
      - T1: earliest available scene
      - T2: latest available scene
    """
    matches = find_matching_bhoonidhi_scenes(bbox)
    if not matches:
        return None

    if target_date:
        try:
            clean = target_date.strip()
            if len(clean) == 7:  # YYYY-MM
                tgt = datetime.strptime(clean, "%Y-%m").date()
            elif len(clean) == 4:  # YYYY
                tgt = datetime.strptime(f"{clean}-06", "%Y-%m").date()
            else:
                tgt = datetime.strptime(clean[:10], "%Y-%m-%d").date()
            matches.sort(key=lambda x: abs((x[0] - tgt).days))
            print(f"--> [Bhoonidhi] Matched closest scene for target date '{target_date}': {matches[0][0]} ({matches[0][2][:25]}...)", flush=True)
            return matches[0]
        except Exception as e:
            print(f"--> [Bhoonidhi] Could not parse target date '{target_date}': {e}. Using date_tag order.", flush=True)

    if date_tag == "T1" and len(matches) > 1:
        return matches[0]
    return matches[-1]


def format_bhoonidhi_window(date_tag: str, target_date: Optional[str] = None) -> str:
    """Format RFC3339 datetime interval for Bhoonidhi STAC query (<365 days to prevent HTTP 406)."""
    import calendar
    from datetime import timedelta
    if target_date:
        clean = target_date.strip()
        try:
            if len(clean) == 7:  # YYYY-MM
                y, m = map(int, clean.split("-"))
                last_d = calendar.monthrange(y, m)[1]
                return f"{clean}-01T00:00:00Z/{clean}-{last_d:02d}T23:59:59Z"
            elif len(clean) == 10:  # YYYY-MM-DD
                d = datetime.strptime(clean, "%Y-%m-%d").date()
                s_d = d - timedelta(days=30)
                e_d = d + timedelta(days=30)
                return f"{s_d}T00:00:00Z/{e_d}T23:59:59Z"
            elif len(clean) == 4:  # YYYY
                return f"{clean}-01-01T00:00:00Z/{clean}-12-31T23:59:59Z"
        except Exception:
            pass

    if date_tag == "T1":
        return "2019-11-01T00:00:00Z/2020-03-31T23:59:59Z"

    # For T2: Query recent 270 days up to current date (guaranteed < 365 days to prevent Bhoonidhi HTTP 406)
    now = datetime.now()
    s_d = now - timedelta(days=270)
    return f"{s_d.strftime('%Y-%m-%d')}T00:00:00Z/{now.strftime('%Y-%m-%d')}T23:59:59Z"


def ingest_bhoonidhi_ephemeral(
    bbox: tuple,
    date_tag: str = "T2",
    target_date: Optional[str] = None,
    timeout: float = 360.0,
) -> Optional[Tuple[datetime.date, str, np.ndarray, Dict[str, Any]]]:
    """
    Ponytail Strategy 2: "Clip & Discard" Ephemeral Ingestion.
    1. Search Bhoonidhi STAC for online scene covering bbox.
    2. Try candidate scenes in order (handling NRSC HTTP 404 archive cold-storage gracefully).
    3. If requested window has only archived scenes, automatically fall back to recent online window.
    4. Stream-download ZIP to ephemeral scratch file.
    5. Stream /vsizip/ to extract ONLY the bbox (~4MB 6-channel stack).
    6. Store the ~4MB raster in MongoDB GridFS.
    7. UNLINK / DELETE the ~200MB+ ZIP immediately in a finally block!
    Returns (date, source_label, stack, metadata) or None if unavailable.
    """
    user = os.environ.get("BHOONIDHI_USER")
    pwd = os.environ.get("BHOONIDHI_PASSWORD")
    if not user or not pwd:
        return None

    from bhoonidhi_client import is_circuit_broken
    if is_circuit_broken():
        print(f"--> [Bhoonidhi Ephemeral] Circuit breaker active. Skipping background fetch.", flush=True)
        return None

    # Check if already in MongoDB
    cached = mrc.get_cached_raster(bbox, date_tag)
    if cached:
        stack, source_label, metadata = cached
        if source_label and "ISRO Bhoonidhi" in source_label:
            dt_str = metadata.get("date")
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d").date() if dt_str else datetime.now().date()
            except Exception:
                dt = datetime.now().date()
            minx, miny, maxx, maxy = bbox
            h, w = stack.shape[1], stack.shape[2]
            from rasterio.transform import from_origin
            safe_prof = {
                "driver": "GTiff",
                "height": h,
                "width": w,
                "count": 6,
                "dtype": "float32",
                "crs": metadata.get("crs", "EPSG:4326"),
                "transform": from_origin(minx, maxy, (maxx - minx) / max(1, w), (maxy - miny) / max(1, h)),
            }
            return dt, source_label, stack, safe_prof

    client = BhoonidhiClient(user, pwd)
    primary_window = format_bhoonidhi_window(date_tag, target_date)
    windows_to_try = [primary_window]

    # If primary window is historical or custom, add recent online window as a fallback
    from datetime import timedelta
    now = datetime.now()
    recent_online_window = f"{(now - timedelta(days=270)).strftime('%Y-%m-%d')}T00:00:00Z/{now.strftime('%Y-%m-%d')}T23:59:59Z"
    if recent_online_window not in windows_to_try:
        windows_to_try.append(recent_online_window)

    scratch_dir = OUTPUTS_DIR / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    scratch_zip = scratch_dir / f"bhoonidhi_{uuid.uuid4().hex[:8]}.zip"
    target_res = 10.0

    best_scene = None
    pid = None
    pcol = None

    for dt_window in windows_to_try:
        print(f"--> [Bhoonidhi Ephemeral] Searching catalog for {date_tag} (window: {dt_window})...", flush=True)
        try:
            scenes = client.search_scenes(bbox, dt_window, collection="ResourceSat-2A_LISS3_BOA", limit=5)
            if not scenes:
                scenes = client.search_scenes(bbox, dt_window, collection="ResourceSat-2A_LISS3_L2", limit=5)
        except Exception as e:
            print(f"--> [Bhoonidhi Ephemeral] STAC search error for window {dt_window}: {e}", flush=True)
            continue

        if not scenes:
            print(f"--> [Bhoonidhi Ephemeral] No LISS-III scenes found for window {dt_window}", flush=True)
            continue

        # Try up to 4 candidate scenes in this window to find an active online scene
        for candidate in scenes[:4]:
            cand_id = candidate.get("id")
            cand_col = candidate.get("collection", "ResourceSat-2A_LISS3_BOA")
            cand_dt = candidate.get("properties", {}).get("datetime", "")
            try:
                print(f"--> [Bhoonidhi Ephemeral] Attempting candidate {cand_id[:25]} ({cand_dt[:10]})...", flush=True)
                client.download_scene_zip(cand_id, cand_col, scratch_zip, timeout=timeout)
                if scratch_zip.exists() and scratch_zip.stat().st_size > 1024:
                    best_scene = candidate
                    pid = cand_id
                    pcol = cand_col
                    break
            except urllib.error.HTTPError as he:
                if he.code == 404:
                    print(f"--> [Bhoonidhi Ephemeral] Scene {cand_id[:25]} is archived by NRSC (HTTP 404). Trying next candidate...", flush=True)
                    continue
                else:
                    print(f"--> [Bhoonidhi Ephemeral] Download error {he.code} for {cand_id[:25]}. Trying next candidate...", flush=True)
                    continue
            except Exception as de:
                print(f"--> [Bhoonidhi Ephemeral] Download attempt failed for {cand_id[:25]}: {de}. Trying next candidate...", flush=True)
                continue

        if best_scene:
            break

    if not best_scene or not scratch_zip.exists() or scratch_zip.stat().st_size <= 1024:
        print(f"--> [Bhoonidhi Ephemeral] No online downloadable LISS-III scenes found across tested windows.", flush=True)
        return None

    try:
        stem = pid
        # Stream directly out of zip via GDAL /vsizip/
        base_vsi = f"/vsizip/{scratch_zip.resolve().as_posix()}/{stem}"
        with rasterio.open(f"{base_vsi}/BAND2.tif") as src0:
            src_crs = src0.crs
            minx, miny, maxx, maxy = transform_bounds("EPSG:4326", src_crs, *bbox)
            target_w = max(1, round((maxx - minx) / target_res))
            target_h = max(1, round((maxy - miny) / target_res))
            target_transform = rasterio.transform.from_origin(minx, maxy, target_res, target_res)
            target_profile = {
                "driver": "GTiff",
                "height": target_h,
                "width": target_w,
                "transform": target_transform,
                "count": 6,
                "dtype": "float32",
                "crs": src_crs,
            }
            win = from_bounds(minx, miny, maxx, maxy, transform=src0.transform)
            green_raw = src0.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        with rasterio.open(f"{base_vsi}/BAND3.tif") as src_red:
            red_raw = src_red.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        with rasterio.open(f"{base_vsi}/BAND4.tif") as src_nir:
            nir_raw = src_nir.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        red = red_raw.astype("float32") / 10000.0
        green = green_raw.astype("float32") / 10000.0
        nir = nir_raw.astype("float32") / 10000.0
        blue = np.clip(green * 0.7 + red * 0.3, 0.0, 1.0)

        eps = 1e-6
        ndvi = np.clip((nir - red) / (nir + red + eps), -1.0, 1.0)
        ndwi = np.clip((green - nir) / (green + nir + eps), -1.0, 1.0)

        stack = np.stack([red, green, blue, nir, ndvi, ndwi], axis=0).astype("float32")
        dt = parse_bhoonidhi_date(stem) or datetime.now().date()
        source_label = f"ISRO Bhoonidhi (Resourcesat-2A LISS-III, {dt})"

        # Commit ~4MB tensor to MongoDB GridFS with clean BSON serializable metadata
        mongo_meta = {"date": str(dt), "product_id": stem, "crs": str(src_crs)}
        mrc.save_cached_raster(bbox, date_tag, stack, source_label, metadata=mongo_meta)
        mrc.log_ingestion_audit(
            action="EPHEMERAL_BHOONIDHI_INGESTION", aoi_name="Watershed", bbox=bbox,
            date_tag=date_tag, source=source_label, tier=1, latency_s=0.0, product_id=stem
        )
        print(f"--> [Bhoonidhi Ephemeral] SUCCESS! Committed ~4MB raster for {pid[:25]} to MongoDB GridFS.", flush=True)
        return dt, source_label, stack, target_profile
    except Exception as e:
        print(f"--> [Bhoonidhi Ephemeral] Error processing {pid}: {e}", flush=True)
        return None
    finally:
        # ponytail: Deletion before addition -- unconditionally clean up large zip and temp files!
        if scratch_zip.exists():
            scratch_zip.unlink(missing_ok=True)
        tmp = scratch_zip.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        print(f"--> [Bhoonidhi Ephemeral] Cleaned up temporary ZIP from disk (0 MB disk remaining).", flush=True)


def load_or_fetch_optical_date(
    bbox: tuple,
    date_tag: str,
    raw_path: Path,
    stack_path: Path,
    on_step: callable = None,
    target_date: str = None,
    cancel_check: callable = None,
) -> tuple[datetime.date, str]:
    """
    Unified optical ingestion with Ponytail simplicity:
    0. Tier 0: Check MongoDB GridFS Clipped Raster Cache (<50ms).
    1. Tier 1: ISRO Bhoonidhi (local ZIP /vsizip/ or live STAC download within 15s budget).
    2. Tier 2: Automated AWS S3 Sentinel-2 L2A STAC fallback (4s range reads).
    All successful fetches are saved to MongoDB GridFS and logged to audit_logs.
    """
    import time
    t_start = time.time()
    fallback_reason = None
    target_res = 10.0

    def _check():
        if cancel_check and (cancel_check() if callable(cancel_check) else cancel_check.is_set()):
            raise InterruptedError("Optical data ingestion cancelled by client")

    def step(m):
        _check()
        if on_step:
            on_step(m)

    _check()

    # 0. TIER 0: MongoDB Clipped Raster Cache (<50ms)
    cached_raster = mrc.get_cached_raster(bbox, date_tag)
    if cached_raster is not None:
        stack, source_label, metadata = cached_raster
        dt_str = metadata.get("date")
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d").date() if dt_str else datetime.now().date()
        except Exception:
            dt = datetime.now().date()

        step(f"[{date_tag}] Serving pre-clipped 6-channel raster from MongoDB GridFS (<50ms)...")
        minx, miny, maxx, maxy = bbox
        prof_dict = metadata.get("profile")
        if prof_dict and "transform" in prof_dict:
            target_profile = prof_dict.copy()
        else:
            from rasterio.transform import from_origin
            target_profile = {
                "driver": "GTiff", "height": stack.shape[1], "width": stack.shape[2],
                "count": 6, "dtype": "float32", "crs": metadata.get("crs", "EPSG:4326"),
                "transform": from_origin(minx, maxy, (maxx - minx) / stack.shape[2], (maxy - miny) / stack.shape[1]),
            }

        atomic_raster_write(stack_path, stack, target_profile)
        four_band = (np.clip(stack[:4], 0.0, 1.0) * 10000.0).astype("uint16")
        raw_profile = target_profile.copy()
        raw_profile.update(count=4, dtype="uint16")
        atomic_raster_write(raw_path, four_band, raw_profile)

        mrc.log_ingestion_audit(
            action="CACHE_HIT", aoi_name="Watershed", bbox=bbox, date_tag=date_tag,
            source=source_label, tier=0, latency_s=time.time() - t_start,
            product_id=metadata.get("product_id"),
        )
        return dt, source_label

    # 1. TIER 1: ISRO Bhoonidhi
    # Check local ZIP cache first
    bhoonidhi_match = find_best_bhoonidhi_scene(bbox, date_tag=date_tag, target_date=target_date)

    # If not found locally, query live Bhoonidhi STAC
    # Note: Full Bhoonidhi scenes are 400MB-1.2GB ZIPs. Downloading them on-the-fly during a live
    # web request causes 90s+ timeouts. Live download is enabled only if BHOONIDHI_LIVE_DOWNLOAD=true
    # (e.g. during offline CLI prewarming via bhoonidhi_prewarm.py).
    allow_live_download = os.environ.get("BHOONIDHI_LIVE_DOWNLOAD", "false").lower() == "true"
    if not bhoonidhi_match and os.environ.get("BHOONIDHI_USER") and allow_live_download:
        try:
            step(f"[{date_tag}] Searching live ISRO Bhoonidhi STAC catalog (Tier 1)...")
            client = BhoonidhiClient()
            dt_window = format_bhoonidhi_window(date_tag, target_date)
            # Try Surface Reflectance (BOA) then Top of Atmosphere (L2)
            scenes = client.search_scenes(bbox, dt_window, collection="ResourceSat-2A_LISS3_BOA", limit=5)
            if not scenes:
                scenes = client.search_scenes(bbox, dt_window, collection="ResourceSat-2A_LISS3_L2", limit=5)

            if scenes:
                best_scene = scenes[0]
                pid = best_scene.get("id")
                pcol = best_scene.get("collection", "ResourceSat-2A_LISS3_BOA")
                zip_path = BHOONIDHI_DIR / f"{pid}.zip"
                step(f"[{date_tag}] Downloading Bhoonidhi scene {pid[:20]}... (15s budget)")
                try:
                    client.download_scene_zip(pid, pcol, zip_path, timeout=15.0)
                    bhoonidhi_match = find_best_bhoonidhi_scene(bbox, date_tag=date_tag, target_date=target_date)
                except Exception as down_err:
                    print(f"--> [Bhoonidhi] Live download aborted ({down_err}). Engaging AWS S3 fallback.", flush=True)
                    fallback_reason = str(down_err)
            else:
                fallback_reason = f"No online Bhoonidhi scenes found in window {dt_window}"
        except Exception as api_err:
            print(f"--> [Bhoonidhi] API search failed ({api_err}). Engaging AWS S3 fallback.", flush=True)
            fallback_reason = str(api_err)
    elif not bhoonidhi_match:
        fallback_reason = "Bhoonidhi local scene not pre-warmed; engaged fast AWS S3 windowed streaming"

    if bhoonidhi_match:
        dt, zpath, stem = bhoonidhi_match
        step(f"[{date_tag}] Ingesting ISRO Bhoonidhi Resourcesat-2A LISS-III ({dt}) via /vsizip/...")
        print(f"--> [Bhoonidhi] Ingesting {date_tag} from {stem[:35]}... (date: {dt})", flush=True)

        base_vsi = f"/vsizip/{zpath.resolve().as_posix()}/{stem}"
        with rasterio.open(f"{base_vsi}/BAND2.tif") as src0:
            src_crs = src0.crs
            minx, miny, maxx, maxy = transform_bounds("EPSG:4326", src_crs, *bbox)
            target_w = max(1, round((maxx - minx) / target_res))
            target_h = max(1, round((maxy - miny) / target_res))
            target_transform = rasterio.transform.from_origin(minx, maxy, target_res, target_res)
            target_profile = src0.profile.copy()
            target_profile.update(
                height=target_h, width=target_w, transform=target_transform,
                count=6, dtype="float32", crs=src_crs
            )
            win = from_bounds(minx, miny, maxx, maxy, transform=src0.transform)
            green_raw = src0.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        with rasterio.open(f"{base_vsi}/BAND3.tif") as src_red:
            red_raw = src_red.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        with rasterio.open(f"{base_vsi}/BAND4.tif") as src_nir:
            nir_raw = src_nir.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

        red = red_raw.astype("float32") / 10000.0
        green = green_raw.astype("float32") / 10000.0
        nir = nir_raw.astype("float32") / 10000.0
        # ponytail: synthesize blue proxy from Green & Red (LISS-3 lacks native blue)
        blue = np.clip(green * 0.7 + red * 0.3, 0.0, 1.0)

        eps = 1e-6
        ndvi = np.clip((nir - red) / (nir + red + eps), -1.0, 1.0)
        ndwi = np.clip((green - nir) / (green + nir + eps), -1.0, 1.0)

        stack = np.stack([red, green, blue, nir, ndvi, ndwi], axis=0).astype("float32")

        # Save 6-channel stack
        atomic_raster_write(stack_path, stack, target_profile)

        # Save 4-band raw tif (RGB-NIR) for NDVI trend / visualization
        four_band = np.stack([red, green, blue, nir], axis=0) * 10000.0
        raw_profile = target_profile.copy()
        raw_profile.update(count=4, dtype="uint16")
        atomic_raster_write(raw_path, four_band.astype("uint16"), raw_profile)

        source_label = f"ISRO Bhoonidhi (Resourcesat-2A LISS-III, {dt})"

        # Save clipped 4MB raster into MongoDB GridFS for sub-50ms repeat reads
        mrc.save_cached_raster(
            bbox, date_tag, stack, source_label,
            metadata={"date": str(dt), "product_id": stem, "crs": str(src_crs)}
        )
        mrc.log_ingestion_audit(
            action="SATELLITE_INGESTION", aoi_name="Watershed", bbox=bbox, date_tag=date_tag,
            source=source_label, tier=1, latency_s=time.time() - t_start, product_id=stem
        )
        return dt, source_label

    # 2. TIER 2: Fallback to AWS STAC Sentinel-2
    from data_download import search_scene, clip_scene_to_stack
    from preprocessing import build_6channel_stack
    import calendar

    custom_window = None
    if target_date:
        clean = target_date.strip()
        try:
            if len(clean) == 7:  # YYYY-MM
                y, m = map(int, clean.split("-"))
                last_day = calendar.monthrange(y, m)[1]
                custom_window = f"{clean}-01/{clean}-{last_day:02d}"
            elif len(clean) == 10:  # YYYY-MM-DD
                from datetime import timedelta
                d = datetime.strptime(clean, "%Y-%m-%d").date()
                start_d = d - timedelta(days=15)
                end_d = d + timedelta(days=15)
                custom_window = f"{start_d}/{end_d}"
            elif len(clean) == 4:  # YYYY
                custom_window = f"{clean}-01-01/{clean}-12-31"
        except Exception as e:
            print(f"--> [Adapter] Error formatting custom_window from '{target_date}': {e}", flush=True)

    step(f"[{date_tag}] Searching Sentinel-2 catalog for imagery (AWS S3 fallback{f', window: {custom_window}' if custom_window else ''})...")
    print(f"--> [Adapter] Searching Sentinel-2 for {date_tag} (custom_window={custom_window}).", flush=True)
    item = search_scene(bbox, date_tag, custom_window=custom_window)
    dt = item.datetime.date()
    step(f"[{date_tag}] Streaming & clipping scene bands ({dt})...")
    clip_scene_to_stack(item, bbox, raw_path, cancel_check=cancel_check)
    _check()
    step(f"[{date_tag}] Computing NDVI / NDWI...")
    build_6channel_stack(raw_path, stack_path)
    _check()
    source_label = f"Copernicus Sentinel-2 L2A (AWS S3 Fallback, {dt})"

    # Read the built stack and store in MongoDB GridFS
    try:
        with rasterio.open(stack_path) as s_src:
            s_data = s_src.read()
            mrc.save_cached_raster(
                bbox, date_tag, s_data, source_label,
                metadata={"date": str(dt), "product_id": item.id, "crs": str(s_src.crs)}
            )
    except Exception as e:
        print(f"--> [Adapter] Note: Could not cache S3 raster in Mongo: {e}", flush=True)

    mrc.log_ingestion_audit(
        action="SATELLITE_INGESTION", aoi_name="Watershed", bbox=bbox, date_tag=date_tag,
        source=source_label, tier=2, latency_s=time.time() - t_start,
        product_id=item.id, fallback_reason=fallback_reason
    )
    return dt, source_label


# ============================================================================
# 3. Cache & Disk Pruner (Keep 2 Recent)
# ============================================================================

def prune_disk_cache(cache_dir: Path = DATA_PROCESSED, max_items: int = 2) -> None:
    """Keep only the `max_items` most recently modified GeoTIFFs on disk."""
    if not cache_dir.exists():
        return
    tifs = sorted(cache_dir.glob("*.tif"), key=os.path.getmtime, reverse=True)
    for old_tif in tifs[max_items:]:
        try:
            old_tif.unlink(missing_ok=True)
        except Exception:
            pass
