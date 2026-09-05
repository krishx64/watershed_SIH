"""
Intervention registry -- tracks individual watershed structures (check dams,
farm ponds, percolation tanks, contour bunds) as first-class records, and
samples the currently-active AOI's already-computed satellite evidence
(land cover, NDVI/NDWI) at each one's exact location.

This is the PS's own gap, not a guess at one: "geo-coded images ... used
only for documentation purposes rather than for integrated spatial analysis
and interpretation" (26015.pdf, verified directly against the source text).
An intervention here is exactly that -- a geo-coded record -- now connected
to satellite evidence and, when nearby, an actual field-verification photo,
instead of sitting as an isolated point on a map.

Persistence follows geo_photo.py's exact pattern (CSV, DictWriter/DictReader,
DATA_PROCESSED.parent as the storage root) rather than inventing a new one.

Honesty note (CLAUDE.md rule 5): Kadwanchi's real structures are IWDP-era
(1997-2002); this project's T1/T2 Sentinel-2 imagery is 2019-20 vs 2024-25 --
both postdate construction by 15+ years. There is no way to show genuine
pre-construction vs post-construction change with this data. Every evidence
readout here is framed as "condition over the available imagery window,"
never "before/after the intervention" -- that phrasing would overclaim what
the data can actually support.
"""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio.warp

from config import DATA_PROCESSED, CLASS_NAMES, NODATA_CLASS

INTERVENTIONS_LOG = DATA_PROCESSED.parent / "interventions.csv"
INTERVENTION_FIELDS = ["id", "name", "type", "lat", "lon", "added_date", "notes"]
INTERVENTION_TYPES = ["Check Dam", "Farm Pond", "Percolation Tank", "Contour Bund", "Other"]

PHOTO_LINK_THRESHOLD_M = 200.0


def add_intervention(name: str, type_: str, lat: float, lon: float, notes: str = "") -> str:
    INTERVENTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not INTERVENTIONS_LOG.exists()
    intervention_id = datetime.now(timezone.utc).strftime("iv_%Y%m%d%H%M%S%f")
    with open(INTERVENTIONS_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INTERVENTION_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "id": intervention_id, "name": name, "type": type_, "lat": lat, "lon": lon,
            "added_date": datetime.now(timezone.utc).date().isoformat(), "notes": notes,
        })
    return intervention_id


def read_interventions() -> list[dict]:
    if not INTERVENTIONS_LOG.exists():
        return []
    with open(INTERVENTIONS_LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latlon_to_pixel(lat: float, lon: float, profile: dict):
    """(lat, lon) -> (row, col) on a raster's grid, or None if outside it.
    Reprojects EPSG:4326 -> profile["crs"] FIRST (profile["transform"] is in
    the raster's own CRS, UTM meters for this project's Sentinel-2 grids --
    applying the transform to raw lat/lon degrees without reprojecting first
    produces silently-wrong pixel indices, not a crash, which is worse)."""
    (x,), (y,) = rasterio.warp.transform("EPSG:4326", profile["crs"], [lon], [lat])
    col, row = ~profile["transform"] * (x, y)
    row, col = int(row), int(col)
    height, width = profile["height"], profile["width"]
    if not (0 <= row < height and 0 <= col < width):
        return None
    return row, col


def _patch(arr2d: np.ndarray, row: int, col: int, radius: int = 2) -> np.ndarray:
    h, w = arr2d.shape
    r0, r1 = max(0, row - radius), min(h, row + radius + 1)
    c0, c1 = max(0, col - radius), min(w, col + radius + 1)
    return arr2d[r0:r1, c0:c1]


def sample_evidence_at_point(lat: float, lon: float, active_aoi: dict) -> dict:
    """Samples the active AOI's already-computed class maps and NDVI/NDWI at
    (lat, lon). class: MODE of a small patch (categorical, matches
    geo_photo.py::predict_class_at_point). NDVI/NDWI: MEAN of the same patch
    -- continuous data, mode would be statistically meaningless here. Do not
    reuse the class-sampling logic for these channels."""
    profile = active_aoi["profile"]
    pixel = latlon_to_pixel(lat, lon, profile)
    if pixel is None:
        return {"in_aoi": False}
    row, col = pixel

    def class_at(class_map):
        patch = _patch(class_map, row, col)
        real = patch[patch != NODATA_CLASS]
        if real.size == 0:
            return None
        values, counts = np.unique(real, return_counts=True)
        return int(values[counts.argmax()])

    def mean_channel(img, channel_idx):
        patch = _patch(img[channel_idx], row, col)
        return float(np.mean(patch))

    class_t1 = class_at(active_aoi["class_t1"])
    class_t2 = class_at(active_aoi["class_t2"])
    return {
        "in_aoi": True,
        "class_t1": class_t1, "class_t1_name": CLASS_NAMES.get(class_t1, "No data"),
        "class_t2": class_t2, "class_t2_name": CLASS_NAMES.get(class_t2, "No data"),
        "ndvi_t1": mean_channel(active_aoi["img_t1"], 4), "ndvi_t2": mean_channel(active_aoi["img_t2"], 4),
        "ndwi_t1": mean_channel(active_aoi["img_t1"], 5), "ndwi_t2": mean_channel(active_aoi["img_t2"], 5),
        "t1_date": active_aoi["t1_date"], "t2_date": active_aoi["t2_date"],
    }


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def link_nearby_photos(lat: float, lon: float, validation_log_rows: list[dict],
                        threshold_m: float = PHOTO_LINK_THRESHOLD_M) -> list[dict]:
    """Geo-tagged field-verification photos (geo_photo.py's log) within
    threshold_m of this intervention -- the actual photo+satellite+GIS
    connection the PS asks for, using data this app already collects."""
    linked = []
    for row in validation_log_rows:
        try:
            d = _haversine_m(lat, lon, float(row["lat"]), float(row["lon"]))
        except (KeyError, ValueError):
            continue
        if d <= threshold_m:
            linked.append({**row, "distance_m": round(d, 1)})
    linked.sort(key=lambda r: r["distance_m"])
    return linked
