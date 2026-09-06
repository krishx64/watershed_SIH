"""
One-time export: run the real, trained Model 1 (+ Tier-1 change detection,
health score, NDVI trend, alerts) against the 3 locally-available trained
sites, and write static PNGs + JSON for the Next.js demo frontend (`web/`) to
read client-side, with no live backend. See the plan's "Part 1" section.

Kadwanchi has a real T1->T2 pair; Tamhini Ghat and Donimalai are single-date,
training-only AOIs (documentation.md section 5) -- exported with
has_change_pair=False so the frontend can honestly disable Change/Health-trend
UI for them instead of faking a change story they don't have.

Run:  .venv/Scripts/python.exe src/export_demo_data.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from PIL import Image

from config import (
    AOI_NAME, AUX_AOIS, CHANGE_CLASS_NAMES, CLASS_COLORS, CLASS_NAMES,
    DATA_PROCESSED, MODELS_DIR, NUM_CLASSES, OUTPUTS_DIR,
)
from model1_unet import build_model
from inference_demo import predict_class_map
from tier1_fallback import run_tier1, summarize_changes
from recommendation_engine import compute_health_score, generate_alerts, ndvi_trend
import torch

# Same accent palette as the frontend's "Watershed-specific accent layer"
# (sage/amber/danger/teal) so the exported change map and the site's design
# tokens agree, rather than the export script inventing its own colors.
CHANGE_CLASS_COLORS = {
    0: (230, 230, 230),  # No change -- neutral gray
    1: (43, 110, 130),   # New water/conservation structure -- teal
    2: (162, 59, 46),    # New construction/built-up -- danger
    3: (166, 106, 22),   # Vegetation/water loss (degradation) -- amber
    4: (78, 122, 61),    # Vegetation gain -- sage
    255: (225, 225, 225),  # No coverage -- matches CLASS_COLORS[NODATA_CLASS], never a change class
}

WEB_PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "demo-data"
DISPLAY_MAX_DIM = 1400


def colorize(class_map: np.ndarray, color_map: dict) -> np.ndarray:
    """Exact-palette RGB colorization, no interpolation -- every output pixel
    is one of color_map's real colors, never a blend (required for the
    full-res classmap_*.png files, which the frontend samples pixel-exact for
    the Field Verify tab)."""
    h, w = class_map.shape
    rgb = np.zeros((h, w, 3), dtype="uint8")
    for cls, color in color_map.items():
        rgb[class_map == cls] = color
    return rgb


def save_png(rgb: np.ndarray, path: Path, resize_max: int | None = None):
    img = Image.fromarray(rgb, mode="RGB")
    if resize_max and max(img.size) > resize_max:
        scale = resize_max / max(img.size)
        new_size = (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale)))
        img = img.resize(new_size, Image.NEAREST)  # NEAREST: stays exact-palette even resized
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  wrote {path.relative_to(WEB_PUBLIC.parent.parent)}")


def wgs84_bounds(profile) -> dict:
    left, bottom, right, top = rasterio.transform.array_bounds(
        profile["height"], profile["width"], profile["transform"]
    )
    west, south, east, north = transform_bounds(profile["crs"], "EPSG:4326", left, bottom, right, top)
    return {"west": west, "south": south, "east": east, "north": north}


def class_hectares(class_map: np.ndarray, pixel_area_m2: float = 100.0) -> dict:
    from config import NODATA_CLASS
    out = {}
    for cls in range(NUM_CLASSES):
        count = int(np.sum(class_map == cls))
        out[str(cls)] = {"name": CLASS_NAMES[cls], "pixels": count, "hectares": round(count * pixel_area_m2 / 10000, 2)}
    n_nodata = int(np.sum(class_map == NODATA_CLASS))
    if n_nodata:
        out[str(NODATA_CLASS)] = {"name": CLASS_NAMES[NODATA_CLASS], "pixels": n_nodata,
                                  "hectares": round(n_nodata * pixel_area_m2 / 10000, 2)}
    return out


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    ckpt_path = MODELS_DIR / "model1_lulc_unet.pt"
    model = build_model().to(device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    print(f"Loaded Model 1 (epoch {ckpt['epoch']}, val_mean_iou={ckpt.get('val_mean_iou', ckpt.get('val_loss', 'n/a'))})")

    sites = [{"key": AOI_NAME, "dates": ["T1", "T2"]}] + [
        {"key": a["name"], "dates": ["S1"]} for a in AUX_AOIS
    ]

    index = []
    for site in sites:
        key, dates = site["key"], site["dates"]
        print(f"\n=== {key} ({'change pair' if len(dates) == 2 else 'single date'}) ===")
        site_dir = WEB_PUBLIC / key

        class_maps, imgs, profile = {}, {}, None
        for tag in dates:
            stack_path = DATA_PROCESSED / f"{key}_{tag}_stack6.tif"
            if not stack_path.exists():
                raise FileNotFoundError(f"Missing {stack_path} -- run data_download.py/preprocessing.py for {key} first.")
            class_map, img, profile = predict_class_map(model, stack_path, device)
            class_maps[tag] = class_map
            imgs[tag] = img
            display_name = "t1" if tag == "T1" else "t2" if tag == "T2" else "s1"
            save_png(colorize(class_map, CLASS_COLORS), site_dir / f"{display_name}.png", resize_max=DISPLAY_MAX_DIM)
            save_png(colorize(class_map, CLASS_COLORS), site_dir / f"classmap_{display_name}.png")

        has_change_pair = len(dates) == 2
        meta = {
            "key": key,
            "bbox_wgs84": wgs84_bounds(profile),
            "class_names": CLASS_NAMES,
            "class_colors": {str(k): list(v) for k, v in CLASS_COLORS.items()},
            "has_change_pair": has_change_pair,
        }

        last_tag = dates[-1]
        display_last = "t2" if has_change_pair else "s1"
        meta["health_score"] = round(compute_health_score(class_maps[last_tag]), 1)
        meta["class_breakdown"] = class_hectares(class_maps[last_tag])

        if has_change_pair:
            change_map = run_tier1(class_maps["T1"], class_maps["T2"])
            save_png(colorize(change_map, CHANGE_CLASS_COLORS), site_dir / "change.png", resize_max=DISPLAY_MAX_DIM)
            meta["change_class_names"] = CHANGE_CLASS_NAMES
            meta["change_class_colors"] = {str(k): list(v) for k, v in CHANGE_CLASS_COLORS.items()}
            meta["change_summary"] = summarize_changes(change_map)
            trend = ndvi_trend(imgs["T1"], imgs["T2"])
            meta["ndvi_trend"] = round(trend, 4)
            meta["alerts"] = generate_alerts(class_maps["T2"], change_map, meta["health_score"], trend)

        (site_dir).mkdir(parents=True, exist_ok=True)
        with open(site_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        print(f"  wrote web/public/demo-data/{key}/meta.json")

        index.append({
            "key": key, "has_change_pair": has_change_pair,
            "health_score": meta["health_score"], "display_last": display_last,
        })

    with open(WEB_PUBLIC / "index.json", "w") as f:
        json.dump(index, f, indent=2)
    print(f"\nDone. wrote web/public/demo-data/index.json ({len(index)} sites)")


if __name__ == "__main__":
    main()
