"""
Rule-based recommendation engine (model_plan.md section 4) — takes Model 1's
class map + the change map (Model 2 or Tier 1 fallback) + a health score, and
emits explainable alerts/recommendations. No ML, no training data needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from config import CLASS_NAMES, NODATA_CLASS

WATER, DENSE_VEG, AGRI, SPARSE_VEG, BARREN, BUILTUP, FALLOW = range(7)

# Health-score weights: how much each class contributes per pixel (0-100 scale).
# "Good" classes (water, dense veg, agriculture) score high; degraded/built-up score low.
CLASS_HEALTH_WEIGHT = {
    WATER: 100,
    DENSE_VEG: 90,
    AGRI: 70,
    SPARSE_VEG: 55,
    FALLOW: 35,
    BUILTUP: 20,
    BARREN: 10,
}


def compute_health_score(class_map: np.ndarray) -> float:
    """Simple, explainable composite: mean of per-pixel class health weights.
    100 = ideal mix of water/vegetation, 0 = fully barren/built-up.
    Pixels with no real satellite coverage (config.NODATA_CLASS) are excluded
    rather than averaged in -- otherwise a partial-scene gap silently pulls
    the score toward whatever weight that pixel's spurious model prediction
    happened to get."""
    valid = class_map != NODATA_CLASS
    if not valid.any():
        return 0.0
    weights = np.vectorize(CLASS_HEALTH_WEIGHT.get)(class_map[valid])
    return float(np.mean(weights))


def ndvi_trend(img_t1: np.ndarray, img_t2: np.ndarray) -> float:
    """Mean NDVI change (channel 4 of the 6-channel R,G,B,NIR,NDVI,NDWI stack);
    negative = declining vegetation vigor. Excludes pixels with no real
    satellite coverage (R,G,B,NIR all exactly 0) in either date -- those read
    as NDVI=0 (0/0), which biases the trend toward zero if left in."""
    no_coverage_t1 = np.all(img_t1[:4] == 0, axis=0)
    no_coverage_t2 = np.all(img_t2[:4] == 0, axis=0)
    valid = ~(no_coverage_t1 | no_coverage_t2)
    if not valid.any():
        return 0.0
    return float(np.mean(img_t2[4][valid]) - np.mean(img_t1[4][valid]))


def generate_alerts(class_map_t2: np.ndarray, change_map: np.ndarray,
                     health_score: float, ndvi_trend_value: float,
                     health_history: list[float] | None = None,
                     known_project_mask: np.ndarray | None = None,
                     pixel_area_m2: float = 100.0) -> list[dict]:
    """
    Applies model_plan.md section 4's rules over the change map, returns a list
    of alert/recommendation dicts (severity, message, area_ha).
    health_history: prior health scores (oldest->newest), for the
    "declining 2+ consecutive periods" rule.
    """
    alerts = []

    def area_ha(mask):
        return round(int(np.sum(mask)) * pixel_area_m2 / 10000, 2)

    construction_mask = change_map == 2
    if construction_mask.any():
        verified = known_project_mask if known_project_mask is not None else np.zeros_like(construction_mask)
        unverified = construction_mask & ~verified
        if unverified.any():
            alerts.append({
                "severity": "ALERT",
                "rule": "new_construction",
                "message": "Possible unauthorized construction detected — recommend field verification.",
                "area_ha": area_ha(unverified),
            })
        if (construction_mask & verified).any():
            alerts.append({
                "severity": "INFO",
                "rule": "new_construction_verified",
                "message": "New construction within a known project boundary — logged, no action needed.",
                "area_ha": area_ha(construction_mask & verified),
            })

    degradation_mask = change_map == 3
    if degradation_mask.any() and ndvi_trend_value < -0.02:
        alerts.append({
            "severity": "RECOMMEND",
            "rule": "degradation_intervention",
            "message": "Vegetation/water loss with declining NDVI trend — soil/water conservation "
                       "structure recommended in this zone.",
            "area_ha": area_ha(degradation_mask),
        })

    new_water_mask = change_map == 1
    if new_water_mask.any():
        matched = known_project_mask if known_project_mask is not None else np.zeros_like(new_water_mask)
        confirmed = new_water_mask & matched
        if confirmed.any():
            alerts.append({
                "severity": "VERIFIED",
                "rule": "new_structure_confirmed",
                "message": "New conservation structure confirmed within a known project — update project records.",
                "area_ha": area_ha(confirmed),
            })
        unmatched = new_water_mask & ~matched
        if unmatched.any():
            alerts.append({
                "severity": "INFO",
                "rule": "new_water_unverified",
                "message": "New water body detected outside known project boundaries — worth a field check.",
                "area_ha": area_ha(unmatched),
            })

    history = list(health_history or []) + [health_score]
    # Trailing run below 40 (model_plan.md 4: "health_score < 40 for 2+
    # consecutive periods"). Counts the trailing streak, not total history
    # length -- [30, 35] rising is still 2 consecutive low periods, [20, 80]
    # is not, even though len(history) is 2 in both cases.
    streak = 0
    for h in reversed(history):
        if h < 40:
            streak += 1
        else:
            break
    if streak >= 2:
        alerts.append({
            "severity": "RECOMMEND",
            "rule": "priority_intervention",
            "message": f"Watershed health persistently low for the last {streak} periods "
                       f"(current score={health_score:.1f}/100) — priority intervention recommended.",
            "area_ha": None,
        })

    if not alerts:
        alerts.append({
            "severity": "INFO",
            "rule": "no_flags",
            "message": "No alerts this period — watershed conditions stable.",
            "area_ha": None,
        })

    return alerts


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    class_map = rng.integers(0, 7, size=(128, 128)).astype("uint8")
    change_map = np.zeros((128, 128), dtype="uint8")
    change_map[40:60, 40:60] = 2  # construction
    change_map[10:30, 10:30] = 3  # degradation

    health = compute_health_score(class_map)
    trend = -0.05
    for alert in generate_alerts(class_map, change_map, health, trend, health_history=[35, 38]):
        print(f"[{alert['severity']}] {alert['message']} (area={alert['area_ha']} ha)")
