"""
Tier 1 change-detection fallback (model_plan.md 3.5) — no ML, pure rule-based
diff of two Model 1 class maps. Build this before Model 2; it's the guaranteed
demo path if the Siamese U-Net doesn't converge in time.

Usable standalone with two numpy class-map arrays (e.g. for a quick demo before
Model 1 is even trained, by feeding it hand-made/synthetic maps).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from scipy import ndimage

from config import CLASS_NAMES, NODATA_CLASS

WATER, DENSE_VEG, AGRI, SPARSE_VEG, BARREN, BUILTUP, FALLOW = range(7)

# 12 connected pixels at 10m/px = 12 * 100 m^2 = 1200 m^2 minimum mappable unit.
MIN_BLOB_PIXELS_DEFAULT = 12


def diff_to_change_map(class_t1: np.ndarray, class_t2: np.ndarray) -> np.ndarray:
    """Per-pixel change class (model_plan.md 3.3), from two same-shape class maps.
    Pixels with no real satellite coverage in either date (NODATA_CLASS=255)
    are assigned NODATA_CLASS in the output -- excluded from change statistics,
    never booked as "No change". Without this, a partial-scene gap silently
    inflates the "No change" hectares.

    Rules are deliberately conservative (unlisted transitions stay "No change"):
    dense_veg->water/builtup, dense/agri->barren, barren->sparse and similar
    are plausible in the real world but indistinguishable from classifier noise
    at current accuracy -- expanding them without validation would trade
    under-reporting for false alarms."""
    assert class_t1.shape == class_t2.shape
    change = np.zeros(class_t1.shape, dtype="uint8")  # 0 = no change

    nodata = (class_t1 == NODATA_CLASS) | (class_t2 == NODATA_CLASS)

    new_water = np.isin(class_t1, [BARREN, SPARSE_VEG, AGRI, FALLOW]) & (class_t2 == WATER)
    change[new_water] = 1

    new_builtup = np.isin(class_t1, [BARREN, SPARSE_VEG, AGRI, FALLOW, WATER]) & (class_t2 == BUILTUP)
    change[new_builtup] = 2

    degradation = np.isin(class_t1, [DENSE_VEG, WATER]) & (class_t2 == BARREN)
    change[degradation] = 3

    veg_gain = np.isin(class_t1, [BARREN, FALLOW, SPARSE_VEG]) & np.isin(class_t2, [DENSE_VEG, AGRI])
    change[veg_gain] = 4

    change[nodata] = NODATA_CLASS
    return change


def filter_small_blobs(change_map: np.ndarray, min_pixels: int = MIN_BLOB_PIXELS_DEFAULT) -> np.ndarray:
    """Drop connected regions smaller than min_pixels, per change class (noise filter).
    NODATA_CLASS pixels are never filtered -- they are missing data, not noise."""
    cleaned = change_map.copy()
    for cls in np.unique(change_map):
        if cls == 0 or cls == NODATA_CLASS:
            continue
        cls_mask = change_map == cls
        labeled, n = ndimage.label(cls_mask)
        sizes = ndimage.sum(cls_mask, labeled, range(1, n + 1))
        for blob_id, size in enumerate(sizes, start=1):
            if size < min_pixels:
                cleaned[labeled == blob_id] = 0
    return cleaned


def geofence_mask(change_map: np.ndarray, watershed_mask: np.ndarray | None) -> np.ndarray:
    """Zero out change outside the watershed boundary, if a boundary mask is given.
    watershed_mask: same-shape bool array, True = inside watershed. None = no geofence applied.
    NODATA_CLASS pixels stay NODATA_CLASS even outside the boundary -- missing
    data must not become "No change" via geofencing."""
    if watershed_mask is None:
        return change_map
    out = change_map.copy()
    clear = ~watershed_mask & (out != NODATA_CLASS)
    out[clear] = 0
    return out


def summarize_changes(change_map: np.ndarray, pixel_area_m2: float = 100.0) -> dict:
    """Area (in hectares) per change class, for reporting/demo.
    NODATA_CLASS pixels are excluded from every class total (they are not
    "No change" hectares). Use int((change_map == NODATA_CLASS).sum()) at the
    call site if the no-coverage area itself needs reporting."""
    from config import CHANGE_CLASS_NAMES
    summary = {}
    for cls, name in CHANGE_CLASS_NAMES.items():
        px_count = int(np.sum(change_map == cls))
        summary[name] = {
            "pixels": px_count,
            "hectares": round(px_count * pixel_area_m2 / 10000, 2),
        }
    return summary


def run_tier1(class_t1: np.ndarray, class_t2: np.ndarray, watershed_mask=None,
              min_blob_pixels: int = MIN_BLOB_PIXELS_DEFAULT) -> np.ndarray:
    """Full Tier-1 pipeline: diff -> geofence -> noise filter."""
    change = diff_to_change_map(class_t1, class_t2)
    change = geofence_mask(change, watershed_mask)
    change = filter_small_blobs(change, min_blob_pixels)
    return change


if __name__ == "__main__":
    # Smoke test with synthetic class maps (useful before Model 1 is trained).
    rng = np.random.default_rng(0)
    t1 = rng.integers(0, 7, size=(128, 128)).astype("uint8")
    t2 = t1.copy()
    t2[40:55, 40:55] = BUILTUP  # inject a fake "new construction" blob
    t2[10:13, 10:13] = BARREN  # inject a too-small blob (should get filtered)

    change = run_tier1(t1, t2)
    print("Change class pixel counts:", dict(zip(*np.unique(change, return_counts=True))))
    print(summarize_changes(change))
